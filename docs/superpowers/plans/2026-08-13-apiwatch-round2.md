# APIWatch Round 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the two improvements surfaced by the Saleor 3.7.0 real-repo test: richer change descriptions for the patch agent, and mapper precision against generic resource-name collisions.

**Architecture:** Two independent tasks (parallelizable) plus an integration task. Task A adds per-entry detail fetching to the Stripe watcher (each table-format changelog entry links a `.md` detail page with full prose — fetch it lazily, only for changes that survive mapping, so we never fetch hundreds of pages). Task B makes the mapper two-tier: snake_case attribute symbols are primary evidence; CapitalCase resource symbols only count in files that also contain a primary match, and no file counts unless it mentions the API's name at all. Task C wires both into the CLI.

**Tech Stack:** unchanged (Python 3.11, PyYAML, stdlib urllib, pytest).

**Spec:** `docs/spec.md` + findings recorded in this plan's rationale (Saleor test: Stripe `Product`/`Transaction`/`Authorization` changes matched 1216/62/24 call sites of Saleor's own domain models; table-format entries carry title-only descriptions).

## Global Constraints

- Same as round 1 (see `2026-08-13-apiwatch-mvp.md`): PyYAML only, draft PRs only, never merge, skip dirs, 25+ existing tests must stay green.
- Detail fetching must be lazy (only for changes that have call sites after mapping) and failure-tolerant (a failed fetch falls back to the title-only description, never crashes the run).
- Mapper API-mention filter must be configurable and default on: `require_api_mention: true` in config.

---

### Task A: Detail-page enrichment (watcher)

**Files:**
- Modify: `apiwatch/watcher/stripe.py`
- Test: `tests/test_watcher_stripe.py` (append)

**Interfaces:**
- Produces: `enrich_change(change: ChangeEntry, fetch: Callable[[str], str] | None = None) -> ChangeEntry` in `apiwatch/watcher/stripe.py`. Returns a new `ChangeEntry` whose `description` is the fetched detail-page markdown body (whitespace-normalized, capped at 4000 chars) and whose `symbols` are the union of existing symbols and symbols extracted from the body (existing first, order preserved). `fetch` defaults to `apiwatch.watcher.core.load_source`; any exception from fetch returns the change unchanged. If `change.url` is empty or does not end with `.md`, return the change unchanged.

- [ ] **Step 1: Write failing tests** (append to `tests/test_watcher_stripe.py`)

```python
def test_enrich_change_fetches_detail_and_merges_symbols():
    from apiwatch.models import ChangeEntry
    from apiwatch.watcher.stripe import enrich_change

    change = ChangeEntry(
        api="stripe", version="2022-11-15",
        title="Removes the `charges` attribute from the `PaymentIntent` object",
        description="Removes the `charges` attribute from the `PaymentIntent` object",
        breaking=True, symbols=("charges", "PaymentIntent"),
        url="https://docs.stripe.com/changelog/2022-11-15/removes-charges-attribute-paymentintent.md",
    )
    detail = "# Detail\n\nUse the new `latest_charge` field, expandable via `expand`.\n"
    enriched = enrich_change(change, fetch=lambda url: detail)
    assert "latest_charge" in enriched.description
    assert enriched.symbols[:2] == ("charges", "PaymentIntent")
    assert "latest_charge" in enriched.symbols
    assert enriched.version == change.version


def test_enrich_change_fetch_failure_returns_unchanged():
    from apiwatch.models import ChangeEntry
    from apiwatch.watcher.stripe import enrich_change

    def boom(url):
        raise OSError("network down")

    change = ChangeEntry("stripe", "2022-11-15", "t", "orig", True, ("charges",), "https://x/y.md")
    assert enrich_change(change, fetch=boom).description == "orig"


def test_enrich_change_non_md_url_skipped():
    from apiwatch.models import ChangeEntry
    from apiwatch.watcher.stripe import enrich_change

    calls = []
    change = ChangeEntry("stripe", "2022-11-15", "t", "orig", True, (), "https://x/upgrades#2022-11-15")
    enrich_change(change, fetch=lambda url: calls.append(url) or "body")
    assert calls == []
```

- [ ] **Step 2: Run to verify FAIL** — `python3 -m pytest tests/test_watcher_stripe.py -q`
- [ ] **Step 3: Implement** in `apiwatch/watcher/stripe.py`:

```python
from dataclasses import replace

_DETAIL_CAP = 4000


def enrich_change(change, fetch=None):
    """Fetch the entry's detail page for a fuller description and symbol set.

    Table-format changelog entries carry only their title; the linked .md
    detail page has the full prose (including replacement guidance the patch
    agent needs). Failure-tolerant: any fetch problem returns the change as-is.
    """
    if not change.url.endswith(".md"):
        return change
    if fetch is None:
        from apiwatch.watcher.core import load_source
        fetch = load_source
    try:
        body = fetch(change.url)
    except Exception:
        return change
    description = " ".join(body.split())[:_DETAIL_CAP]
    if not description:
        return change
    merged = list(change.symbols)
    for sym in extract_symbols(body):
        if sym not in merged:
            merged.append(sym)
    return replace(change, description=description, symbols=tuple(merged))
```

- [ ] **Step 4: Run to verify PASS** (full suite too: `python3 -m pytest -q`)
- [ ] **Step 5: Commit** — `git add -A && git commit` message `feat: enrich changes with detail-page prose before patching`, ending with the standard session footer used by prior commits (see `git log`).

---

### Task B: Two-tier mapper relevance

**Files:**
- Modify: `apiwatch/mapper.py`
- Test: `tests/test_mapper.py` (append)

**Interfaces:**
- Changes `scan_repo` signature to `scan_repo(root, symbols, extensions=(".py",), api_name: str | None = None)`. Behavior:
  - Symbols are classified: **primary** = contains a lowercase letter and (has `_` or is all-lowercase) — e.g. `charges`, `purchase_details`, `latest_charge`; **secondary** = everything else — e.g. `PaymentIntent`, `Product`.
  - A file's matches count only if the file has at least one primary-symbol match. Secondary-only files yield no call sites. If there are no primary symbols at all, secondary symbols are used alone (fall back to old behavior).
  - If `api_name` is given, a file yields call sites only if the file's text contains `api_name` case-insensitively.
  - Existing callers passing only `(root, symbols)` keep working.

- [ ] **Step 1: Write failing tests** (append to `tests/test_mapper.py`)

```python
def test_secondary_symbols_alone_do_not_flag(tmp_path):
    (tmp_path / "models.py").write_text(
        "import stripe\nclass Transaction:\n    purchase_total = 0\n"
    )
    assert scan_repo(tmp_path, ["purchase_details", "Transaction"]) == []


def test_secondary_counts_alongside_primary_in_same_file(tmp_path):
    (tmp_path / "api.py").write_text(
        "import stripe\npi = stripe.PaymentIntent.retrieve(x)\ncharge = pi.charges.data[0]\n"
    )
    sites = scan_repo(tmp_path, ["charges", "PaymentIntent"])
    assert {(s.line, s.symbol) for s in sites} == {(2, "PaymentIntent"), (3, "charges")}


def test_api_name_mention_required(tmp_path):
    (tmp_path / "own.py").write_text("charges = compute_charges()\n")
    (tmp_path / "vendor.py").write_text("import stripe\ncharges = pi.charges\n")
    sites = scan_repo(tmp_path, ["charges"], api_name="stripe")
    assert {s.file for s in sites} == {"vendor.py"}


def test_only_secondary_symbols_falls_back(tmp_path):
    (tmp_path / "api.py").write_text("import stripe\npi = stripe.PaymentIntent.retrieve(x)\n")
    sites = scan_repo(tmp_path, ["PaymentIntent"])
    assert len(sites) == 1
```

- [ ] **Step 2: Run to verify FAIL** — note `test_secondary_symbols_alone_do_not_flag` and existing `test_scan_multiple_symbols` must BOTH pass after implementation; do not regress existing tests.
- [ ] **Step 3: Implement** — rework the inner loop of `scan_repo`:

```python
def _is_primary(symbol: str) -> bool:
    return symbol.islower() or "_" in symbol


def scan_repo(root, symbols, extensions=(".py",), api_name=None):
    root = Path(root)
    usable = [s for s in symbols if len(s) >= MIN_SYMBOL_LEN]
    primary = [s for s in usable if _is_primary(s)]
    secondary = [s for s in usable if not _is_primary(s)]
    if not primary:
        primary, secondary = secondary, []
    patterns = {s: re.compile(rf"\b{re.escape(s)}\b") for s in primary + secondary}
    sites: list[CallSite] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts[:-1]):
            continue
        text = path.read_text(errors="replace")
        if api_name and api_name.lower() not in text.lower():
            continue
        if not any(patterns[s].search(text) for s in primary):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for sym, pat in patterns.items():
                if pat.search(line):
                    sites.append(CallSite(
                        file=str(path.relative_to(root)), line=lineno,
                        snippet=line.strip(), symbol=sym,
                    ))
    return sites
```

- [ ] **Step 4: Run full suite to verify PASS** — `python3 -m pytest -q`
- [ ] **Step 5: Commit** — message `feat: two-tier mapper relevance to kill resource-name false positives`, same footer convention as prior commits.

---

### Task C: CLI integration (after A and B land)

**Files:**
- Modify: `apiwatch/cli.py`, `apiwatch/config.py`, `tests/test_cli_e2e.py`

**Interfaces:**
- Consumes: `enrich_change` (Task A), new `scan_repo` signature (Task B).
- Config gains `require_api_mention: true` default (config.py DEFAULTS).
- In `_run_api`: pass `api_name=name if cfg["require_api_mention"] else None` to `scan_repo`; after a change survives the call-site guard and dry-run check, call `change = enrich_change(change)` before `build_prompt`, then re-scan? **No** — do not re-scan; enrichment may add symbols but the site list and allowlist stay as mapped (deterministic, and avoids fetch-order coupling).

- [ ] **Step 1: Write failing e2e test** (append to `tests/test_cli_e2e.py`): repo file `own.py` containing `charges = 1` but no mention of stripe must not be patched or listed:

```python
def test_files_without_api_mention_are_ignored(target):
    repo, origin, gh, gh_log = target
    (repo / "own.py").write_text("charges = [1]\n")
    import subprocess as sp
    sp.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
            "add", "own.py"], check=True)
    sp.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "-q", "-m", "own"], check=True)
    count = run(repo, repo / "apiwatch.yml", runner=_fake_runner, gh_cmd=str(gh))
    assert count == 1
    show = sp.run(["git", "-C", str(origin), "show", "apiwatch/stripe-2022-11-15-1:own.py"],
                  capture_output=True, text=True, check=True).stdout
    assert show == "charges = [1]\n"
```

- [ ] **Step 2: Verify FAIL, implement, verify PASS** (full suite).
- [ ] **Step 3: Update README** — replace the "Symbol matching is a heuristic" caveat with the two-tier + api-mention behavior; mention detail-page enrichment.
- [ ] **Step 4: Commit + push** to `claude/code-it-4rij2l` (PR #1 updates automatically).

## Self-Review Notes

- Task A and B touch disjoint files → safe to parallelize; Task C is the only cli.py toucher.
- The `_fake_runner` e2e fixture's `app.py` contains `import stripe` so the api-mention filter keeps existing e2e tests passing; `test_mapper.py` existing tests pass because they don't pass `api_name` and their fixtures contain primary symbol `charges` matches (billing.py has none, .apiwatch skipped) — `test_scan_multiple_symbols` has both primary+secondary in app.py → unchanged expectations.
- Saleor replay of this plan: `fuel`(primary)+`Authorization`(secondary) → files must contain `fuel` AND mention stripe → 0 sites → no agent run; `purchase_details` likewise; `features`+`Product` → files must contain `features` and stripe-mention → small honest set instead of 1216.
