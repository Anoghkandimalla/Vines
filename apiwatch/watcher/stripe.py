"""Parse Stripe's prose changelog into structured entries.

Stripe has no machine-readable changelog, so this extracts structure from the
markdown document, in both formats Stripe has used:

- table format (current, e.g. https://docs.stripe.com/changelog.md): one
  `## <version>` heading per API version (dates, optionally suffixed like
  `2026-07-29.dahlia`), with tables whose rows carry a linked title and an
  explicit Breaking / Non-breaking column;
- bullet format (older upgrade guides): `### Breaking changes` / other
  subsections containing bullet entries.
"""
import re
from dataclasses import replace

from apiwatch.models import ChangeEntry

_VERSION_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}(?:\.\w+)?)\s*$", re.MULTILINE)
_SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^-\s+(.+?)(?=^-\s|\Z)", re.MULTILINE | re.DOTALL)
_TABLE_ROW_RE = re.compile(
    r"^\|\s*\[(?P<title>.+?)\]\((?P<url>[^)]+)\)\s*\|[^|]*\|\s*(?P<breaking>Breaking|Non-breaking)\s*\|",
    re.MULTILINE,
)
_SYMBOL_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def extract_symbols(text: str) -> tuple[str, ...]:
    seen: list[str] = []
    for sym in _SYMBOL_RE.findall(text):
        if sym not in seen:
            seen.append(sym)
    return tuple(seen)


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


def parse_changelog(text: str, url: str = "") -> list[ChangeEntry]:
    entries: list[ChangeEntry] = []
    versions = list(_VERSION_RE.finditer(text))
    for i, vm in enumerate(versions):
        version = vm.group(1)
        end = versions[i + 1].start() if i + 1 < len(versions) else len(text)
        body = text[vm.end():end]
        for tm in _TABLE_ROW_RE.finditer(body):
            title = " ".join(tm.group("title").split())
            entries.append(
                ChangeEntry(
                    api="stripe",
                    version=version,
                    title=title[:80],
                    description=title,
                    breaking=tm.group("breaking") == "Breaking",
                    symbols=extract_symbols(title),
                    url=tm.group("url"),
                )
            )
        sections = list(_SECTION_RE.finditer(body))
        for j, sm in enumerate(sections):
            heading = sm.group(1)
            s_end = sections[j + 1].start() if j + 1 < len(sections) else len(body)
            breaking = "breaking" in heading.lower()
            for bm in _BULLET_RE.finditer(body[sm.end():s_end]):
                desc = " ".join(bm.group(1).split())
                entries.append(
                    ChangeEntry(
                        api="stripe",
                        version=version,
                        title=desc[:80],
                        description=desc,
                        breaking=breaking,
                        symbols=extract_symbols(desc),
                        url=f"{url}#{version}" if url else "",
                    )
                )
    return entries
