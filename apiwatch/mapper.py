"""Find usages of changed API symbols in the target repo.

Symbols are split into two tiers: snake_case attribute names (primary) are real
evidence of API usage, while CapitalCase resource names (secondary) only count in
files that already contain a primary match — avoiding false positives on an app's
own domain models. If only secondary symbols are given, they are treated as primary.

Primary symbols only count where they read like API field access in Python:
attribute access (`.coupon`), a quoted key or value (`["coupon"]`,
`fields="sms_pumping_risk"`), or a keyword argument (`coupon=`). A bare word
(a local variable, English in a docstring or message) is not evidence.
"""
import re
from pathlib import Path
from typing import Sequence

from apiwatch.models import CallSite

# migrations: generated schema history, never hand-patched.
SKIP_DIRS = {".git", ".apiwatch", "node_modules", "venv", ".venv", "__pycache__", "migrations"}
MIN_SYMBOL_LEN = 3


def _is_primary(symbol: str) -> bool:
    return symbol.islower() or "_" in symbol


def _field_pattern(symbol: str) -> re.Pattern:
    s = re.escape(symbol)
    return re.compile(rf"\.{s}\b|([\"']){s}\1|(?:^|[(,])\s*{s}=(?!=)", re.MULTILINE)


def repo_mentions(root: Path, token: str, extensions: tuple[str, ...] = (".py",)) -> bool:
    """True if any scanned file contains token (case-insensitive)."""
    root = Path(root)
    token = token.lower()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts[:-1]):
            continue
        if token in path.read_text(errors="replace").lower():
            return True
    return False


def scan_repo(
    root: Path,
    symbols: Sequence[str],
    extensions: tuple[str, ...] = (".py",),
    api_name: str | None = None,
    resources: Sequence[str] = (),
) -> list[CallSite]:
    root = Path(root)
    usable = [s for s in symbols if len(s) >= MIN_SYMBOL_LEN]
    primary = [s for s in usable if _is_primary(s)]
    secondary = [s for s in usable if not _is_primary(s)]
    if not primary:
        primary, secondary = secondary, []
    patterns = {s: _field_pattern(s) for s in primary}
    patterns.update({s: re.compile(rf"\b{re.escape(s)}\b") for s in secondary})
    sites: list[CallSite] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts[:-1]):
            continue
        text = path.read_text(errors="replace")
        if api_name and api_name.lower() not in text.lower():
            continue
        if resources:
            # "PromotionCode" should match promotion_code / promotionCode too.
            squashed = re.sub(r"[_\s]", "", text.lower())
            if not any(r.lower() in squashed for r in resources):
                continue
        if not any(patterns[s].search(text) for s in primary):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for sym, pat in patterns.items():
                if pat.search(line):
                    sites.append(
                        CallSite(
                            file=str(path.relative_to(root)),
                            line=lineno,
                            snippet=line.strip(),
                            symbol=sym,
                        )
                    )
    return sites


FIXTURE_DIRS = {"fixtures", "tests", "test", "testdata"}
FIXTURE_EXTENSIONS = (".json", ".yaml", ".yml")
MAX_FIXTURES = 20


def related_fixtures(root: Path, sites: Sequence[CallSite], symbols: Sequence[str]) -> list[str]:
    """Test fixtures near the affected code that carry a changed symbol.

    A patch that changes how code reads a response usually breaks the tests
    feeding it recorded payloads, so the agent may update those too. Scope is
    kept tight: data files under a test/fixture directory beneath an affected
    file's own directory, containing a primary symbol, at most MAX_FIXTURES.
    """
    root = Path(root)
    primary = [s for s in symbols if len(s) >= MIN_SYMBOL_LEN and _is_primary(s)]
    if not primary:
        return []
    # Data files quote field names as keys; no access-pattern rule needed.
    patterns = [re.compile(rf"\b{re.escape(s)}\b") for s in primary]
    found: set[str] = set()
    for base in sorted({(root / s.file).parent for s in sites}):
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in FIXTURE_EXTENSIONS:
                continue
            parts = path.relative_to(root).parts[:-1]
            if SKIP_DIRS & set(parts) or not FIXTURE_DIRS & set(parts):
                continue
            text = path.read_text(errors="replace")
            if any(p.search(text) for p in patterns):
                found.add(str(path.relative_to(root)))
    return sorted(found)[:MAX_FIXTURES]
