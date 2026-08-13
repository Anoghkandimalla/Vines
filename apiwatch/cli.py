"""apiwatch CLI: the entry point the GitHub Action runs on a schedule."""
import argparse
import subprocess
import sys
from pathlib import Path

from apiwatch.config import load_config
from apiwatch.mapper import scan_repo
from apiwatch.patcher.agent import run_agent
from apiwatch.patcher.pr import open_draft_pr
from apiwatch.patcher.prompt import build_prompt
from apiwatch.state import load_state, save_state
from apiwatch.watcher.core import load_source, new_breaking_changes
from apiwatch.watcher.stripe import parse_changelog


def _branch_exists_on_origin(repo: Path, branch: str) -> bool:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-remote", "--heads", "origin", branch],
        capture_output=True, text=True, check=True,
    ).stdout
    return bool(out.strip())


def _changed_files(repo: Path, state_file: str) -> list[str]:
    """Working-tree changes including untracked files, excluding the state file."""
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    files = []
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        if path != state_file and not path.startswith(state_file.split("/")[0] + "/"):
            files.append(path)
    return files


def _restore_tree(repo: Path, state_file: str) -> None:
    """Drop all working-tree changes and untracked files, sparing the state file."""
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "clean", "-fdq", "-e", state_file.split("/")[0]],
        check=True,
    )


def _run_api(repo: Path, cfg: dict, api: dict, state: dict, state_path: Path,
             dry_run: bool, runner, gh_cmd: str, max_call_sites: int) -> int:
    name = api["name"]
    source = str(api["changelog"])
    state_file = cfg["state_file"]
    entries = parse_changelog(load_source(source), url=source)
    if not entries:
        # A healthy changelog source never parses to nothing — likely a
        # format change or an unsupported page, so shout instead of no-opping.
        print(f"[apiwatch] WARNING: {name}: changelog source parsed to 0 entries; check {source}")
        return 0
    last = state.get(name, {}).get("last_version")
    if last is None:
        # First run: seed the watermark at the newest version instead of
        # proposing patches for every breaking change in the API's history.
        newest_available = max(e.version for e in entries)
        print(f"[apiwatch] {name}: first run; seeding watermark at {newest_available}, proposing nothing")
        if not dry_run:
            state[name] = {"last_version": newest_available}
            save_state(state_path, state)
        return 0
    changes = new_breaking_changes(entries, last)
    proposed = 0
    newest = last
    per_version: dict[str, int] = {}
    for change in changes:
        sites = scan_repo(repo, change.symbols)
        newest = max(newest, change.version)
        if not sites:
            print(f"[apiwatch] {name} {change.version}: breaking change does not affect this repo: {change.title}")
            continue
        if len(sites) > max_call_sites:
            # A generic symbol (e.g. a resource name that collides with the
            # app's own domain models) can match huge swaths of the repo;
            # patching that automatically would be reckless. Flag for a human.
            print(f"[apiwatch] WARNING: {name} {change.version}: {len(sites)} call sites exceeds "
                  f"max_call_sites={max_call_sites}; too broad to patch automatically, "
                  f"review manually: {change.title} ({change.url})")
            continue
        per_version[change.version] = per_version.get(change.version, 0) + 1
        branch = f"apiwatch/{name}-{change.version}-{per_version[change.version]}"
        if dry_run:
            proposed += 1
            print(f"[apiwatch] DRY RUN: would propose patch for {name} {change.version} "
                  f"({len(sites)} call sites): {change.title}")
            continue
        if _branch_exists_on_origin(repo, branch):
            print(f"[apiwatch] {name} {change.version}: branch {branch} already on origin "
                  "(open PR awaiting review?); skipping")
            continue
        print(f"[apiwatch] {name} {change.version}: patching {len(sites)} call sites: {change.title}")
        allowed = sorted({s.file for s in sites})
        try:
            run_agent(repo, build_prompt(change, sites), runner=runner)
            touched = _changed_files(repo, state_file)
            if not touched:
                print(f"[apiwatch] agent produced no changes for {name} {change.version}; skipping PR")
                continue
            outside = sorted(set(touched) - set(allowed))
            if outside:
                # The prompt asks the agent to stay inside the affected files;
                # this makes that a hard policy rather than a request.
                print(f"[apiwatch] WARNING: {name} {change.version}: agent touched files outside "
                      f"the affected set ({', '.join(outside)}); discarding patch")
                continue
            state[name] = {"last_version": newest}
            save_state(state_path, state)
            open_draft_pr(repo, change, branch=branch, base=cfg["base_branch"],
                          paths=allowed, extra_paths=[state_file], gh_cmd=gh_cmd)
            proposed += 1
        finally:
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", cfg["base_branch"]], check=False)
            _restore_tree(repo, state_file)
    if not dry_run and newest != last and proposed == 0:
        state[name] = {"last_version": newest}
        save_state(state_path, state)
    return proposed


def run(repo: Path, config_path: Path, dry_run: bool = False, runner=None, gh_cmd: str = "gh",
        max_call_sites: int | None = None) -> int:
    repo = Path(repo)
    cfg = load_config(config_path)
    if max_call_sites is None:
        max_call_sites = cfg["max_call_sites"]
    state_path = repo / cfg["state_file"]
    state = load_state(state_path)
    proposed = 0
    failed = []
    for api in cfg["apis"]:
        try:
            proposed += _run_api(repo, cfg, api, state, state_path, dry_run, runner, gh_cmd,
                                 max_call_sites)
        except Exception as exc:
            failed.append(api["name"])
            print(f"[apiwatch] ERROR: {api['name']}: {exc}")
    if failed:
        raise RuntimeError(f"apiwatch failed for: {', '.join(failed)}")
    return proposed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="apiwatch")
    sub = parser.add_subparsers(dest="command", required=True)
    runp = sub.add_parser("run", help="check watched APIs and propose patches")
    runp.add_argument("--repo", default=".", type=Path)
    runp.add_argument("--config", default="apiwatch.yml", type=Path)
    runp.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    count = run(args.repo, args.config, dry_run=args.dry_run)
    print(f"[apiwatch] done: {count} patch(es) proposed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
