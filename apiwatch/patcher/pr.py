"""Commit agent edits to a branch and open a DRAFT pull request.

Hard safety rule: this tool only ever proposes patches. Nothing here (or
anywhere in apiwatch) ever combines a PR into its base branch.
"""
import re
import subprocess
from pathlib import Path

from apiwatch.models import ChangeEntry


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "-c", "user.email=apiwatch@localhost", "-c", "user.name=apiwatch"]
        + list(args),
        check=True,
    )


_GITHUB_REMOTE_RE = re.compile(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$")


def github_repo_slug(remote_url: str) -> str | None:
    """`owner/name` for a GitHub remote URL (https or ssh), else None."""
    m = _GITHUB_REMOTE_RE.search(remote_url.strip())
    return f"{m[1]}/{m[2]}" if m else None


def open_draft_pr(
    repo_root: Path,
    change: ChangeEntry,
    branch: str,
    base: str,
    paths: list[str] | None = None,
    extra_paths: list[str] | None = None,
    gh_cmd: str = "gh",
) -> None:
    repo_root = Path(repo_root)
    _git(repo_root, "checkout", "-b", branch)
    if paths:
        _git(repo_root, "add", "--", *paths)
    else:
        _git(repo_root, "add", "-A")
    for p in extra_paths or []:
        _git(repo_root, "add", "-f", p)
    title = f"[apiwatch] {change.api} {change.version}: {change.title}"
    _git(repo_root, "commit", "-m", title)
    _git(repo_root, "push", "-u", "origin", branch)
    body = (
        f"Automated patch proposal for a breaking change in the **{change.api}** API "
        f"(version `{change.version}`).\n\n"
        f"**What changed upstream:** {change.description}\n\n"
        f"**Changelog:** {change.url}\n\n"
        "This PR was opened as a draft by apiwatch and is **never auto-merged** — "
        "please review the patch before accepting it.\n"
    )
    # Name the repo explicitly: in a fork, `gh pr create` otherwise targets
    # the upstream parent, which apiwatch must never open PRs against.
    origin_url = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True, text=True, check=True,
    ).stdout
    slug = github_repo_slug(origin_url)
    repo_args = ["--repo", slug] if slug else []
    try:
        subprocess.run(
            [gh_cmd, "pr", "create", *repo_args, "--draft", "--base", base, "--head", branch,
             "--title", title, "--body", body],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        # The command line carries the whole PR body; surface gh's own reason
        # (e.g. Actions not permitted to create PRs) instead of burying it.
        reason = (exc.stderr or exc.stdout or "").strip() or f"exit status {exc.returncode}"
        print(f"[apiwatch] ERROR: could not open draft PR for {branch}: {reason}")
        if "not permitted to create" in reason:
            print("[apiwatch] hint: enable Settings -> Actions -> General -> Workflow permissions -> "
                  "'Allow GitHub Actions to create and approve pull requests'")
        # A pushed branch without its PR would make later runs skip this
        # change as "awaiting review" forever, so take the branch back down.
        subprocess.run(["git", "-C", str(repo_root), "push", "-q", "origin", "--delete", branch],
                       check=False)
        raise
