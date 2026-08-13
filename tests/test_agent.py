import subprocess

from apiwatch.patcher.agent import run_agent


def _git_repo(tmp_path):
    def run(cmd):
        subprocess.run(cmd, shell=True, cwd=tmp_path, check=True)

    run("git init -q -b main && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init")
    (tmp_path / "app.py").write_text("charge = pi.charges.data[0]\n")
    run("git add -A && git -c user.email=t@t -c user.name=t commit -q -m app")


def test_run_agent_returns_diff_of_edits(tmp_path):
    _git_repo(tmp_path)

    def fake_runner(repo_root, prompt):
        (repo_root / "app.py").write_text(
            'pi = stripe.PaymentIntent.retrieve(pid, expand=["latest_charge"])\ncharge = pi.latest_charge\n'
        )

    diff = run_agent(tmp_path, "prompt text", runner=fake_runner)
    assert "-charge = pi.charges.data[0]" in diff
    assert "+charge = pi.latest_charge" in diff


def test_run_agent_no_changes_returns_empty(tmp_path):
    _git_repo(tmp_path)
    diff = run_agent(tmp_path, "prompt", runner=lambda root, prompt: None)
    assert diff == ""
