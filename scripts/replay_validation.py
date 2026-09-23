"""Historical replay validation (spec Week 1 + Week 2 milestones).

Replays a real, documented past breaking change against a repo pinned to just
before it, using the REAL claude CLI as the patch agent. Prints the evidence
and exits nonzero on any failed check.

Scenarios (pass one or more names; default runs all):
  stripe  Stripe 2022-11-15: `charges` removed from PaymentIntent by default;
          `latest_charge` added.
  twilio  Twilio 2024-02-09 (twilio-python 8.13.0): Lookup v2 `carrier` field
          removed from `sms_pumping_risk`; `carrier_risk_category` remains.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

SCENARIOS = {
    "stripe": {
        "label": "Stripe 2022-11-15",
        "repo": "replay_repo",
        "changelog": "stripe_changelog.md",
        "watermark": "2022-08-01",
        "branch": "apiwatch/stripe-2022-11-15-1",
        "checks": [
            ("patch removed default reliance on pi.charges",
             lambda src: "pi.charges" not in src),
            ("patch uses latest_charge or expand (the documented fix)",
             lambda src: "latest_charge" in src or "expand" in src),
        ],
    },
    "twilio": {
        "label": "Twilio 2024-02-09 (twilio-python 8.13.0)",
        "repo": "twilio_replay_repo",
        "changelog": "twilio_changelog.md",
        "watermark": "2024-01-25",
        "branch": "apiwatch/twilio-2024-02-09-1",
        "checks": [
            ("patch no longer reads the removed sms_pumping_risk carrier field",
             lambda src: not re.search(r"""\[\s*["']carrier["']\s*\]""", src)),
            ("patch uses carrier_risk_category or line_type_intelligence (the replacements)",
             lambda src: "carrier_risk_category" in src or "line_type_intelligence" in src),
        ],
    },
}


def replay(name: str) -> bool:
    sc = SCENARIOS[name]
    tmp = Path(tempfile.mkdtemp(prefix=f"apiwatch-replay-{name}-"))
    origin = tmp / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp / "repo"
    shutil.copytree(FIXTURES / sc["repo"], repo)
    (repo / "apiwatch.yml").write_text(
        f"apis:\n  - name: {name}\n    changelog: {FIXTURES / sc['changelog']}\n"
    )
    state = repo / ".apiwatch" / "state.json"
    state.parent.mkdir()
    # Rolled back to just before the change shipped:
    state.write_text(json.dumps({name: {"last_version": sc["watermark"]}}))
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", f"pre-change {name} consumer"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"], check=True)
    gh = tmp / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> {tmp / "gh_log.txt"}\n')
    gh.chmod(0o755)

    from apiwatch.cli import run

    print(f"=== REPLAY: detection + patch for {sc['label']} ===")
    count = run(repo, repo / "apiwatch.yml", gh_cmd=str(gh))

    checks = [("watcher+mapper proposed exactly 1 patch", count == 1)]
    branch = sc["branch"]
    patched = subprocess.run(
        ["git", "-C", str(origin), "show", f"{branch}:app.py"],
        capture_output=True, text=True,
    ).stdout
    checks += [(label, bool(patched) and check(patched)) for label, check in sc["checks"]]
    compile_target = tmp / "patched_app.py"
    compile_target.write_text(patched)
    compiled = bool(patched) and subprocess.run(
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
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print(f"\nReplay validation ({name}): {'PASS' if ok else 'FAIL'}  (workdir kept at {tmp})\n")
    return ok


def main(argv: list[str]) -> int:
    names = argv or list(SCENARIOS)
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        print(f"unknown scenario(s): {', '.join(unknown)}; choose from {', '.join(SCENARIOS)}")
        return 2
    results = {n: replay(n) for n in names}
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
