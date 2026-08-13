"""Historical replay validation (spec Week 1 + Week 2 milestones).

Replays the real Stripe 2022-11-15 breaking change (`charges` removed from
PaymentIntent by default; `latest_charge` added) against a repo pinned to
just before it, using the REAL claude CLI as the patch agent. Prints the
evidence and exits nonzero on any failed check.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="apiwatch-replay-"))
    origin = tmp / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp / "repo"
    shutil.copytree(FIXTURES / "replay_repo", repo)
    (repo / "apiwatch.yml").write_text(
        f"apis:\n  - name: stripe\n    changelog: {FIXTURES / 'stripe_changelog.md'}\n"
    )
    state = repo / ".apiwatch" / "state.json"
    state.parent.mkdir()
    # Rolled back to just before the 2022-11-15 change shipped:
    state.write_text(json.dumps({"stripe": {"last_version": "2022-08-01"}}))
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "pre-2022-11-15 stripe consumer"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
    gh = tmp / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {tmp / "gh_log.txt"}\n')
    gh.chmod(0o755)

    from apiwatch.cli import run

    print("=== REPLAY: detection + patch for Stripe 2022-11-15 ===")
    count = run(repo, repo / "apiwatch.yml", gh_cmd=str(gh))

    checks = []
    checks.append(("watcher+mapper proposed exactly 1 patch", count == 1))
    branch = "apiwatch/stripe-2022-11-15-1"
    patched = subprocess.run(
        ["git", "-C", str(origin), "show", f"{branch}:app.py"],
        capture_output=True, text=True,
    ).stdout
    checks.append(("patch removed default reliance on pi.charges", "pi.charges" not in patched))
    checks.append((
        "patch uses latest_charge or expand (the documented fix)",
        "latest_charge" in patched or "expand" in patched,
    ))
    compile_target = tmp / "patched_app.py"
    compile_target.write_text(patched)
    compiled = subprocess.run(
        [sys.executable, "-m", "py_compile", str(compile_target)]
    ).returncode == 0
    checks.append(("patched file is valid Python", compiled))
    log = (tmp / "gh_log.txt").read_text() if (tmp / "gh_log.txt").exists() else ""
    checks.append(("a DRAFT PR was opened (never merged)", "--draft" in log and "pr merge" not in log))

    print("\n=== PATCHED FILE ===\n" + patched)
    print("=== DIFF ===")
    subprocess.run(["git", "-C", str(origin), "diff", f"main..{branch}", "--", "app.py"])
    print("\n=== CHECKS ===")
    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print(f"\nReplay validation: {'PASS' if ok else 'FAIL'}  (workdir kept at {tmp})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
