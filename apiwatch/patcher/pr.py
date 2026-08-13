"""Commit agent edits to a branch and open a DRAFT pull request.

Hard safety rule: this tool only ever proposes patches. Nothing here (or
anywhere in apiwatch) ever combines a PR into its base branch.
"""
import subprocess
from pathlib import Path

from apiwatch.models import ChangeEntry


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "-c", "user.email=apiwatch@localhost", "-c", "user.name=apiwatch"]
        + list(args),
        check=True,
    )


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
    subprocess.run(
        [gh_cmd, "pr", "create", "--draft", "--base", base, "--head", branch,
         "--title", title, "--body", body],
        cwd=repo_root,
        check=True,
    )
