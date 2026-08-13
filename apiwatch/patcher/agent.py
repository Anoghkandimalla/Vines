"""Run a coding agent against the repo and capture what it changed."""
import subprocess
from pathlib import Path
from typing import Callable

Runner = Callable[[Path, str], None]


def _claude_cli_runner(repo_root: Path, prompt: str) -> None:
    subprocess.run(
        ["claude", "-p", prompt, "--permission-mode", "acceptEdits"],
        cwd=repo_root,
        check=True,
        timeout=600,
    )


def run_agent(repo_root: Path, prompt: str, runner: Runner | None = None) -> str:
    repo_root = Path(repo_root)
    (runner or _claude_cli_runner)(repo_root, prompt)
    return subprocess.run(
        ["git", "-C", str(repo_root), "diff"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
