import json
import stat
import subprocess
from pathlib import Path

import pytest

from apiwatch.cli import run
from apiwatch.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "stripe_changelog.md"


TWILIO_FIXTURE = Path(__file__).parent / "fixtures" / "twilio_changelog.md"


def _make_target(tmp_path, app_text, config_text, state):
    """A consuming repo with a local origin, the given state, and apiwatch config."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    (repo / "app.py").write_text(app_text)
    (repo / "apiwatch.yml").write_text(config_text)
    state_path = repo / ".apiwatch" / "state.json"
    state_path.parent.mkdir()
    state_path.write_text(json.dumps(state))
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
    gh_log = tmp_path / "gh_log.txt"
    gh = tmp_path / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {gh_log}\n')
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return repo, origin, gh, gh_log


@pytest.fixture
def target(tmp_path):
    return _make_target(
        tmp_path,
        "import stripe\n"
        "pi = stripe.PaymentIntent.retrieve(pid)\n"
        "charge = pi.charges.data[0]\n",
        f"apis:\n  - name: stripe\n    changelog: {FIXTURE}\n",
        {"stripe": {"last_version": "2022-08-01"}},
    )


@pytest.fixture
def twilio_target(tmp_path):
    return _make_target(
        tmp_path,
        "from twilio.rest import Client\n"
        "client = Client(sid, token)\n"
        "risk = client.lookups.v2.phone_numbers(n).fetch(fields='sms_pumping_risk')\n"
        "carrier = risk.sms_pumping_risk['carrier']\n",
        f"apis:\n  - name: twilio\n    changelog: {TWILIO_FIXTURE}\n",
        {"twilio": {"last_version": "2024-01-25"}},
    )


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


def test_first_run_seeds_watermark_and_proposes_nothing(target):
    repo, origin, gh, gh_log = target
    (repo / ".apiwatch" / "state.json").unlink()
    count = run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh))
    assert count == 0
    assert not gh_log.exists()
    state = json.loads((repo / ".apiwatch" / "state.json").read_text())
    assert state["stripe"]["last_version"] == "2022-11-15"


def test_second_run_with_existing_branch_does_not_crash(target):
    repo, origin, gh, gh_log = target
    assert run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh)) == 1
    # After the first run the repo is back on main with the pre-patch state,
    # so the same change is re-detected — the existing origin branch must be
    # skipped instead of crashing on a non-fast-forward push.
    assert run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh)) == 0
    assert gh_log.read_text().count("pr create") == 1


def test_agent_edits_outside_affected_files_are_discarded(target):
    repo, origin, gh, gh_log = target

    def evil_runner(repo_root, prompt):
        _fake_runner(repo_root, prompt)
        (repo_root / "evil.py").write_text("import os\n")

    count = run(repo, repo / "apiwatch.yml", runner=evil_runner, gh_cmd=str(gh))
    assert count == 0
    assert not gh_log.exists()
    assert not (repo / "evil.py").exists()
    assert "pi.charges.data[0]" in (repo / "app.py").read_text()


def test_changes_with_too_many_call_sites_are_skipped(target):
    repo, origin, gh, gh_log = target
    count = run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh),
                max_call_sites=1)
    assert count == 0
    assert not gh_log.exists()


def test_files_without_api_mention_are_excluded_from_patch_scope(target):
    repo, origin, gh, gh_log = target
    (repo / "own.py").write_text("charges = [1]\n")
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                    "add", "own.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "own"], check=True)
    prompts = []

    def capturing_runner(repo_root, prompt):
        prompts.append(prompt)
        _fake_runner(repo_root, prompt)

    count = run(repo, repo / "apiwatch.yml", runner=capturing_runner, gh_cmd=str(gh))
    assert count == 1
    # own.py never mentions the watched API, so it must not be offered to the agent
    assert "own.py" not in prompts[0]
    assert "app.py" in prompts[0]


def test_e2e_twilio_proposes_draft_pr(twilio_target):
    repo, origin, gh, gh_log = twilio_target
    prompts = []

    def runner(repo_root, prompt):
        prompts.append(prompt)
        app = repo_root / "app.py"
        app.write_text(app.read_text().replace(
            "risk.sms_pumping_risk['carrier']", "risk.sms_pumping_risk['carrier_risk_category']"
        ))

    count = run(repo, repo / "apiwatch.yml", runner=runner, gh_cmd=str(gh))
    # Only the sms_pumping_risk change touches this repo; the other breaking
    # changes in the window (live_activity, Tags, ...) have no call sites.
    assert count == 1
    assert "sms_pumping_risk" in prompts[0] and "twilio" in prompts[0]
    assert "--draft" in gh_log.read_text()
    branches = subprocess.run(
        ["git", "-C", str(origin), "branch", "--list"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert "apiwatch/twilio-2024-02-09-1" in branches
    assert not any(b.startswith("apiwatch/twilio-2024-02-27") for b in branches)
    state = subprocess.run(
        ["git", "-C", str(origin), "show", "apiwatch/twilio-2024-02-09-1:.apiwatch/state.json"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(state)["twilio"]["last_version"] == "2024-02-27"


def test_unknown_format_fails_that_api(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "apiwatch.yml").write_text(f"apis:\n  - name: acme\n    changelog: {FIXTURE}\n")
    with pytest.raises(RuntimeError, match="acme"):
        run(repo, repo / "apiwatch.yml", dry_run=True)


def test_symbol_less_change_is_enriched_before_mapping(tmp_path, monkeypatch):
    """Current Stripe titles name no fields; the detail page supplies them."""
    index = tmp_path / "changelog.md"
    index.write_text(
        "## 2026-03-25.dahlia\n\n| Change | Products | Type |\n| --- | --- | --- |\n"
        "| [Renames the tax IDs property to tax ID](https://docs.stripe.com/c/tax-ids.md)"
        " | Checkout | Breaking |\n"
    )
    detail = ("#### REST API\n\n| Parameters | Change | Resources |\n| --- | --- | --- |\n"
              "| `tax_ids` | Removed | [x](/y) |\n")
    fetched = []
    monkeypatch.setattr("apiwatch.watcher.core.load_source",
                        lambda u: fetched.append(u) or detail if u.endswith("tax-ids.md")
                        else open(u).read())
    repo, origin, gh, gh_log = _make_target(
        tmp_path,
        "import stripe\ns = stripe.checkout.Session.retrieve(sid)\n"
        "ids = s.collected_information.tax_ids\n",
        f"apis:\n  - name: stripe\n    changelog: {index}\n",
        {"stripe": {"last_version": "2025-09-30.clover"}},
    )
    assert run(repo, repo / "apiwatch.yml", dry_run=True) == 1
    assert fetched == ["https://docs.stripe.com/c/tax-ids.md"]


def test_preview_versions_skipped_but_watermark_advances(tmp_path):
    index = tmp_path / "changelog.md"
    index.write_text(
        "## 2026-07-29.preview\n\n| Change | Products | Type |\n| --- | --- | --- |\n"
        "| [Removes the `charges` attribute](https://x/y) | Payments | Breaking |\n"
    )
    repo, origin, gh, gh_log = _make_target(
        tmp_path, "import stripe\ncharge = pi.charges.data[0]\n",
        f"apis:\n  - name: stripe\n    changelog: {index}\n",
        {"stripe": {"last_version": "2026-03-25.dahlia"}},
    )
    assert run(repo, repo / "apiwatch.yml") == 0
    state = json.loads((repo / ".apiwatch" / "state.json").read_text())
    assert state["stripe"]["last_version"] == "2026-07-29.preview"
    (repo / "apiwatch.yml").write_text(
        f"apis:\n  - name: stripe\n    changelog: {index}\n    include_preview: true\n")
    (repo / ".apiwatch" / "state.json").write_text(
        json.dumps({"stripe": {"last_version": "2026-03-25.dahlia"}}))
    assert run(repo, repo / "apiwatch.yml", dry_run=True) == 1


def test_agent_may_update_related_fixtures(target):
    repo, origin, gh, gh_log = target
    fixture = repo / "tests" / "fixtures" / "pi.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{"charges": {"data": []}}\n')
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "fixture"], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "origin", "main"], check=True)

    def runner(repo_root, prompt):
        assert "tests/fixtures/pi.json" in prompt
        _fake_runner(repo_root, prompt)
        (repo_root / "tests" / "fixtures" / "pi.json").write_text('{"latest_charge": "ch_1"}\n')

    assert run(repo, repo / "apiwatch.yml", runner=runner, gh_cmd=str(gh)) == 1
    show = subprocess.run(
        ["git", "-C", str(origin), "show", "apiwatch/stripe-2022-11-15-1:tests/fixtures/pi.json"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "latest_charge" in show


def test_commit_state_persists_first_run_seed(target):
    repo, origin, gh, gh_log = target
    (repo / ".apiwatch" / "state.json").unlink()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(g + ["commit", "-q", "-am", "no state"], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "origin", "main"], check=True)
    assert run(repo, repo / "apiwatch.yml", commit_state=True, gh_cmd=str(gh)) == 0
    state = subprocess.run(
        ["git", "-C", str(origin), "show", "main:.apiwatch/state.json"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(state)["stripe"]["last_version"] == "2022-11-15"
    files = subprocess.run(
        ["git", "-C", str(origin), "show", "--name-only", "--format=", "main"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert files == [".apiwatch/state.json"]
    # An unchanged state file makes no further commit.
    head = subprocess.run(["git", "-C", str(origin), "rev-parse", "main"],
                          capture_output=True, text=True, check=True).stdout
    run(repo, repo / "apiwatch.yml", commit_state=True, gh_cmd=str(gh))
    assert subprocess.run(["git", "-C", str(origin), "rev-parse", "main"],
                          capture_output=True, text=True, check=True).stdout == head
