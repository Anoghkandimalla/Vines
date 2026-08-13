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


def run(repo: Path, config_path: Path, dry_run: bool = False, runner=None, gh_cmd: str = "gh") -> int:
    repo = Path(repo)
    cfg = load_config(config_path)
    state_path = repo / cfg["state_file"]
    state = load_state(state_path)
    proposed = 0
    for api in cfg["apis"]:
        name = api["name"]
        source = str(api["changelog"])
        entries = parse_changelog(load_source(source), url=source)
        last = state.get(name, {}).get("last_version")
        changes = new_breaking_changes(entries, last)
        newest = last
        n = 0
        api_proposed = 0
        for change in changes:
            sites = scan_repo(repo, change.symbols)
            newest = max(newest or "", change.version)
            if not sites:
                print(f"[apiwatch] {name} {change.version}: breaking change does not affect this repo: {change.title}")
                continue
            n += 1
            if dry_run:
                proposed += 1
                print(f"[apiwatch] DRY RUN: would propose patch for {name} {change.version} "
                      f"({len(sites)} call sites): {change.title}")
                continue
            print(f"[apiwatch] {name} {change.version}: patching {len(sites)} call sites: {change.title}")
            diff = run_agent(repo, build_prompt(change, sites), runner=runner)
            if not diff:
                print(f"[apiwatch] agent produced no changes for {name} {change.version}; skipping PR")
                n -= 1
                continue
            proposed += 1
            api_proposed += 1
            state[name] = {"last_version": newest}
            save_state(state_path, state)
            branch = f"apiwatch/{name}-{change.version}-{n}"
            open_draft_pr(repo, change, branch=branch, base=cfg["base_branch"],
                          extra_paths=[cfg["state_file"]], gh_cmd=gh_cmd)
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", cfg["base_branch"]], check=True)
        if not dry_run and newest and newest != last and api_proposed == 0:
            state[name] = {"last_version": newest}
            save_state(state_path, state)
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
