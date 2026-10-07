import subprocess

from apiwatch.patcher.verify import run_tests, scrubbed_env


def test_scrubbed_env_drops_secret_looking_names():
    env = scrubbed_env({"PATH": "/bin", "ANTHROPIC_API_KEY": "k", "GITHUB_TOKEN": "t",
                        "GH_TOKEN": "t", "AWS_SECRET_ACCESS_KEY": "s", "DB_PASSWORD": "p",
                        "HOME": "/root"})
    assert env == {"PATH": "/bin", "HOME": "/root"}


def _repo(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    return tmp_path


def test_run_tests_pass_fail_and_tail(tmp_path):
    repo = _repo(tmp_path)
    assert run_tests(repo, "true").passed
    failed = run_tests(repo, "echo boom; exit 3")
    assert not failed.passed and "boom" in failed.output_tail


def test_run_tests_hides_credentials_and_restores_them(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    key = "http.https://github.com/.extraheader"
    subprocess.run(["git", "-C", str(repo), "config", "--local", key, "AUTHORIZATION: basic x"],
                   check=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    result = run_tests(repo, f"git config --get {key}; echo key=${{ANTHROPIC_API_KEY:-none}}")
    assert "AUTHORIZATION" not in result.output_tail and "key=none" in result.output_tail
    restored = subprocess.run(["git", "-C", str(repo), "config", "--get", key],
                              capture_output=True, text=True).stdout
    assert restored.strip() == "AUTHORIZATION: basic x"


def test_run_tests_timeout_is_a_failure(tmp_path):
    result = run_tests(_repo(tmp_path), "sleep 5", timeout=1)
    assert not result.passed and "timed out" in result.output_tail
