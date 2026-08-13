import json
import stat
import subprocess
from pathlib import Path

import pytest

from apiwatch.cli import run
from apiwatch.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "stripe_changelog.md"


@pytest.fixture
def target(tmp_path):
    """A consuming repo with a local origin, stale state, and apiwatch config."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    (repo / "app.py").write_text(
        "import stripe\n"
        "pi = stripe.PaymentIntent.retrieve(pid)\n"
        "charge = pi.charges.data[0]\n"
    )
    (repo / "apiwatch.yml").write_text(
        f"apis:\n  - name: stripe\n    changelog: {FIXTURE}\n"
    )
    state = repo / ".apiwatch" / "state.json"
    state.parent.mkdir()
    state.write_text(json.dumps({"stripe": {"last_version": "2022-08-01"}}))
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
    gh_log = tmp_path / "gh_log.txt"
    gh = tmp_path / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {gh_log}\n')
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return repo, origin, gh, gh_log


def _fake_runner(repo_root, prompt):
    app = repo_root / "app.py"
    app.write_text(app.read_text().replace(
        "charge = pi.charges.data[0]", "charge = pi.latest_charge"
    ))


def test_config_defaults(tmp_path):
    p = tmp_path / "apiwatch.yml"
    p.write_text("apis:\n  - name: stripe\n    changelog: /x/log.md\n")
    cfg = load_config(p)
    assert cfg["state_file"] == ".apiwatch/state.json"
    assert cfg["base_branch"] == "main"
    assert cfg["apis"][0]["name"] == "stripe"


def test_e2e_proposes_draft_pr_and_updates_state(target):
    repo, origin, gh, gh_log = target
    count = run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh))
    assert count == 1
    log = gh_log.read_text()
    assert "pr create" in log and "--draft" in log
    branches = subprocess.run(
        ["git", "-C", str(origin), "branch", "--list"], capture_output=True, text=True, check=True
    ).stdout
    assert "apiwatch/stripe-2022-11-15-1" in branches
    show = subprocess.run(
        ["git", "-C", str(origin), "show", "apiwatch/stripe-2022-11-15-1:app.py"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "latest_charge" in show and "pi.charges" not in show
    state = subprocess.run(
        ["git", "-C", str(origin), "show", "apiwatch/stripe-2022-11-15-1:.apiwatch/state.json"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(state)["stripe"]["last_version"] == "2022-11-15"


def test_e2e_dry_run_changes_nothing(target):
    repo, origin, gh, gh_log = target
    count = run(repo, repo / "apiwatch.yml", dry_run=True, runner=_fake_runner, gh_cmd=str(gh))
    assert count == 1
    assert not gh_log.exists()
    assert "charges" in (repo / "app.py").read_text()


def test_e2e_no_new_changes_is_noop(target):
    repo, origin, gh, gh_log = target
    state = repo / ".apiwatch" / "state.json"
    state.write_text(json.dumps({"stripe": {"last_version": "2022-11-15"}}))
    count = run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh))
    assert count == 0
    assert not gh_log.exists()
