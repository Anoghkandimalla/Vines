# Kickoff prompt: Self-Maintaining API Bot — MVP build

*Paste this whole thing as your first message in a coding session (this one or a fresh one) to start the build.*

---

I want to build the MVP of a tool that watches third-party APIs a codebase depends on, detects breaking changes, and automatically opens a pull request that patches the consuming code to work with the new version — never auto-merged, always a PR for human review. This idea has already been validated: three independent rounds of research across general web search, GitHub Marketplace/topics/Actions, Product Hunt, Hacker News, and Y Combinator's own company/funding directories found no existing product that combines third-party API breaking-change detection with automatic PR-based code patching. Y Combinator's Fall 2026 Requests for Startups named this exact gap ("Self-Maintaining APIs") as still open as of their last update. The closest adjacent things — Optic (discontinued, was detection-only, for API producers not consumers), GitHub's Dependabot-AI-agent feature (covers your own package dependencies, not third-party API integrations), and various unified-integration platforms like Merge.dev — all solve a different problem.

## Validated design for the MVP

**Deployment model:** a GitHub Action — a workflow file plus secrets dropped into a target repo, running on a schedule. No hosting, no GitHub App registration, no database. This is deliberately the smallest thing that's still genuinely installable in a real repo, because the MVP's job is to answer "is the patch quality good enough to trust" and "does anyone want this," not to be a scalable product yet.

**Stack:** Python.

**APIs to target first:** Stripe (structured changelog, huge install base, easy to find real historical breaking changes to test against), plus Twilio and the GitHub API as the second and third targets.

**Three components:**
1. **Watcher** — periodically checks each configured API's changelog/spec for anything new since the last run it recorded. Where a formal spec exists, prefer diffing the spec over parsing prose changelogs; where only a prose changelog exists (like Stripe's), extract structured "what changed" data from it.
2. **Mapper** — scans the target repo for actual usages of whatever the watcher flagged as changed, so the tool only acts on changes that matter to *this* codebase, not every change the vendor ships.
3. **Patcher** — hands the affected call sites plus a description of the change to a coding agent, gets back a patch, and opens it as a draft PR with a clear explanation and a link to the vendor's changelog entry.

**Hard safety rule, non-negotiable for v1:** the tool only ever proposes a patch as a PR. It never auto-merges. This is the whole basis for trusting it enough to point it at a real repo.

**Validation approach — do this before claiming anything "works":** don't wait for a live breaking change to happen. Pick a handful of real, documented past Stripe breaking changes from their changelog archive, roll a test repo back to just before that change shipped, run the watcher+mapper+patcher against it, and check whether the tool correctly detects the change and produces a patch that matches (or reasonably approximates) what was actually needed to fix it. This is the evidence bar for "the detector works" or "the patcher works" — not "it compiled" or "it looks right."

**Milestones:**
- Week 1: watcher correctly detects a known past Stripe breaking change, verified against the historical replay test above.
- Week 2: patcher produces a correct patch against a test repo for that same known change.
- Weeks 3–4: wired into an actual GitHub Action, run end-to-end against 2–3 real repos (your own side projects to start).

## How to work — use these skills as you go

1. Start with the **writing-plans** skill to turn this into a concrete, step-by-step implementation plan before writing any code. This spec is the input to that plan, not a replacement for it.
2. Use **test-driven-development** throughout implementation — tests before code, for the watcher, mapper, and patcher components individually as well as the end-to-end flow.
3. Use **using-git-worktrees** if you need isolation from other work happening in the same repo, or before starting implementation from the plan.
4. Whenever something breaks or behaves unexpectedly — a bad diff, a patch that doesn't apply, a false-positive detection — use **systematic-debugging** before proposing a fix. Don't guess.
5. When the Week 1 and Week 2 milestones are ready to check, use **verification-before-completion** before saying either one "works": actually run the historical-replay test, read the full output, and only then state the result with the evidence attached. "Should detect it" or "looks like a good patch" are not verification — a passing replay run is.
6. Once the implementation is in a working state, use **requesting-code-review** before considering it done, and **finishing-a-development-branch** to decide how to integrate it.

Don't skip the replay-test validation step to save time — the entire point of this MVP is finding out honestly whether the patch quality is good enough to trust, and that's the only step that actually answers that question.
