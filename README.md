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

## Safety and trust boundary

- **Never merges.** Only draft PRs, enforced by tests (no merge code exists).
- **Changelog text is untrusted input.** It is fetched from the vendor and embedded in the agent's prompt, so a compromised or spoofed changelog could try to steer the agent. As defense in depth, apiwatch discards any patch that touches files outside the call sites the mapper identified, and commits only those files (plus the state file) — an agent lured off-task cannot land edits elsewhere in the tree. The draft-PR human review is the final backstop.
- **First run proposes nothing.** With no recorded watermark, apiwatch seeds `.apiwatch/state.json` at the newest changelog version instead of opening PRs for every historical breaking change.
- **Open PRs are not re-proposed.** If the patch branch already exists on origin, the change is skipped until the PR is merged or closed.

## Current scope and caveats (MVP)

- **APIs:** Stripe first. Twilio and the GitHub API are the next targets.
- **Languages:** scans `.py` files only for now.
- **Changelog parsing:** format-specific extraction for both formats Stripe has used — the current table-format index at `https://docs.stripe.com/changelog.md` (the shipped default, validated against the live page: 859 entries parsed, and a dry run against a pre-2022-11-15 fixture repo proposed exactly the one `charges` removal patch out of 123 breaking changes) and the older bullet-format upgrade guides. Where a vendor publishes a formal spec, diffing the spec is the plan. A source that parses to zero entries is loudly warned about rather than silently ignored.
- **Symbol matching is two-tier:** snake_case attribute names (`charges`, `purchase_details`) are primary evidence; CapitalCase resource names (`PaymentIntent`, `Product`) only count in files that also contain a primary match, and by default a file must mention the API's name at all (`require_api_mention`; use `match:` per API when your code refers to the vendor by another string, and set `require_api_mention: false` if affected call sites live in wrapper-consumer files that never name the vendor — the filter trades that recall for far fewer false positives). Changes matching more call sites than `max_call_sites` (default 100) are flagged for human review instead of auto-patched. Before patching, the entry's changelog detail page is fetched (code samples preserved) so both the agent prompt and the PR body carry the vendor's full replacement guidance, not just the headline.
- **State:** the changelog watermark (`.apiwatch/state.json`) is committed as part of each patch PR, so merging the PR also advances the watermark.
