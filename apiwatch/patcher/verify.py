"""Run the repo's own test command to check a patch before proposing it.

The command comes from the repo owner's apiwatch.yml, but the code it runs
includes the agent's edits, and the agent was steered by untrusted changelog
text. So tests run with credentials out of reach: secret-looking variables
are dropped from the environment, and the GitHub token that actions/checkout
stores in the git config is unset for the duration and restored afterwards.
"""
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SECRET_NAME_RE = re.compile(r"TOKEN|SECRET|PASSWORD|API_KEY|CREDENTIAL|PRIVATE_KEY", re.IGNORECASE)
_EXTRAHEADER_KEY_RE = re.compile(r"^http\..*\.extraheader$", re.IGNORECASE)
OUTPUT_TAIL_LINES = 60


@dataclass(frozen=True)
class TestResult:
    passed: bool
    output_tail: str


def scrubbed_env(env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if env is None else env)
    return {k: v for k, v in env.items() if not _SECRET_NAME_RE.search(k)}


def _git_config(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), "config", "--local", *args],
                          capture_output=True, text=True)


def _stash_git_credentials(repo: Path) -> list[tuple[str, str]]:
    """Unset auth headers stored in the repo's git config; return them for restore."""
    listing = _git_config(repo, "--list").stdout
    saved = []
    for line in listing.splitlines():
        key, _, value = line.partition("=")
        if _EXTRAHEADER_KEY_RE.match(key):
            saved.append((key, value))
    for key in {k for k, _ in saved}:
        _git_config(repo, "--unset-all", key)
    return saved


def _restore_git_credentials(repo: Path, saved: list[tuple[str, str]]) -> None:
    for key, value in saved:
        _git_config(repo, "--add", key, value)


def run_tests(repo: Path, command: str, timeout: int = 1200) -> TestResult:
    """Run `command` in the repo with credentials hidden; never raises on failure."""
    repo = Path(repo)
    saved = _stash_git_credentials(repo)
    try:
        proc = subprocess.run(command, shell=True, cwd=repo, env=scrubbed_env(),
                              capture_output=True, text=True, timeout=timeout)
        output, passed = proc.stdout + proc.stderr, proc.returncode == 0
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(partial, bytes):
            partial = partial.decode(errors="replace")
        output, passed = partial + f"\n[apiwatch] test command timed out after {timeout}s", False
    finally:
        _restore_git_credentials(repo, saved)
    tail = "\n".join(output.rstrip().splitlines()[-OUTPUT_TAIL_LINES:])
    return TestResult(passed=passed, output_tail=tail)
