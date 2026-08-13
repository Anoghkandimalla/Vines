# apiwatch

Watches the third-party APIs your codebase depends on, detects breaking changes in their changelogs, and opens a **draft pull request** that patches your consuming code to work with the new version.

**Hard safety rule: apiwatch only ever proposes patches as draft PRs. It never merges anything.** Human review is the whole point.

## How it works

1. **Watcher** — on a schedule, loads each configured API's changelog (URL or file), parses it into structured change entries, and compares against a watermark in `.apiwatch/state.json` to find breaking changes it hasn't seen before. Stripe's prose changelog is the first supported format.
2. **Mapper** — scans *your* repo for actual usages of the symbols each change touches (word-boundary matching, `.py` files). Changes that don't affect your code are recorded and skipped — no noise.
3. **Patcher** — hands the affected call sites plus the vendor's change description to a coding agent (the [Claude Code](https://claude.com/claude-code) CLI), captures the resulting diff, commits it to a branch, and opens a **draft** PR that links the vendor's changelog entry.

## Install (GitHub Action)

Two files and one secret — no hosting, no app registration, no database:

1. Copy `examples/apiwatch.yml` to the root of the repo you want watched and adjust it.
2. Copy `examples/apiwatch-workflow.yml` to `.github/workflows/apiwatch.yml`.
3. Add an `ANTHROPIC_API_KEY` secret to the repo (used by the patch agent).

The workflow runs daily and on manual dispatch. `GITHUB_TOKEN` (provided automatically) is used to push the patch branch and open the draft PR.

## Run locally

```bash
pip install -e .
apiwatch run --repo /path/to/your/repo --config /path/to/your/repo/apiwatch.yml --dry-run
```

`--dry-run` reports what it would patch without invoking the agent or touching git.

## Validation: historical replay

We don't claim "it works" from unit tests alone. `scripts/replay_validation.py` replays a real, documented past breaking change — Stripe API `2022-11-15`, which removed the `charges` property from `PaymentIntent` responses (replaced by `latest_charge`) — against a fixture repo pinned to just before that change shipped, using the real coding agent:

```bash
python scripts/replay_validation.py
```

It verifies, end to end, that the watcher detects the change, the mapper finds the affected call sites, the patcher produces a valid patch implementing the documented fix, and a draft PR (never a merge) is opened. The last run passed all checks; run it yourself to reproduce.

```bash
python -m pytest   # unit + e2e tests (agent faked, git origin local, gh stubbed)
```

## Current scope and caveats (MVP)

- **APIs:** Stripe first. Twilio and the GitHub API are the next targets.
- **Languages:** scans `.py` files only for now.
- **Changelog parsing:** prose-changelog extraction is format-specific (Stripe's version-dated upgrade page). Where a vendor publishes a formal spec, diffing the spec is the plan.
- **State:** the changelog watermark (`.apiwatch/state.json`) is committed as part of each patch PR, so merging the PR also advances the watermark.
