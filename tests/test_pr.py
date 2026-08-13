import stat
import subprocess

from apiwatch.models import ChangeEntry
from apiwatch.patcher.pr import open_draft_pr


def _setup(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    (repo / "app.py").write_text("old\n")
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
    gh_log = tmp_path / "gh_log.txt"
    gh = tmp_path / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {gh_log}\n')
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return repo, origin, gh, gh_log


def _change():
    return ChangeEntry("stripe", "2022-11-15", "charges removed", "desc", True, ("charges",), "https://x")


def test_open_draft_pr_pushes_branch_and_creates_draft(tmp_path):
    repo, origin, gh, gh_log = _setup(tmp_path)
    (repo / "app.py").write_text("new\n")
    open_draft_pr(repo, _change(), branch="apiwatch/stripe-2022-11-15", base="main", gh_cmd=str(gh))
    branches = subprocess.run(
        ["git", "-C", str(origin), "branch", "--list"], capture_output=True, text=True, check=True
    ).stdout
    assert "apiwatch/stripe-2022-11-15" in branches
    log = gh_log.read_text()
    assert "pr create" in log
    assert "--draft" in log
    assert "pr merge" not in log


def test_pr_module_never_merges():
    import inspect

    import apiwatch.patcher.pr as pr

    src = inspect.getsource(pr)
    assert "pr merge" not in src
    assert '"merge"' not in src and "'merge'" not in src
