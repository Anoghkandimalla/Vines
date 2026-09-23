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
_REST_SECTION_RE = re.compile(r"^####\s+REST API\s*$(.*?)(?=^#{2,4}\s|\Z)", re.MULTILINE | re.DOTALL)
_CELLS_RE = re.compile(r"^\|(.*?)\|(.*?)\|")
_BACKTICKED_RE = re.compile(r"`([^`]+)`")
_LINK_TEXT_RE = re.compile(r"\[([^\]]+)\]")
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _breaking_rows(body: str):
    """(fields, resources) for each non-Added, non-enum row of the REST table."""
    section = _REST_SECTION_RE.search(body)
    if not section:
        return
    kind = ""
    for line in section.group(1).splitlines():
        m = _CELLS_RE.match(line.strip())
        if not m or set(m[1].strip()) <= set("- "):
            continue
        fields = _BACKTICKED_RE.findall(m[1])
        if not fields:
            kind = m[1].strip().lower()  # header row: Parameters / Field / Values
            continue
        if kind == "values" or m[2].strip().lower() == "added":
            continue
        cells = line.strip().strip("|").split("|")
        yield fields, _LINK_TEXT_RE.findall(cells[2] if len(cells) > 2 else "")


def detail_symbols(body: str) -> tuple[str, ...]:
    """Fields a detail page says existing code may depend on.

    Read from the page's REST API "Changes" table: `Removed`/`Changed` rows
    only, since added fields (including a rename's new name) can't break
    existing code and already-migrated code uses them. A dotted field
    (`SubscriptionItem.billed_until`) contributes its last part. Enum-value
    tables are skipped: removed values (`custom`, `hosted`) are common words.

    No table, no symbols: without one the page describes client-side
    (Stripe.js) or behavioral changes, and its prose backticks enum values
    and ordinary words that only ever matched unrelated code.
    """
    seen: list[str] = []
    for fields, _ in _breaking_rows(body):
        for field in fields:
            name = field.split(".")[-1]
            if _IDENT_RE.match(name) and name not in seen:
                seen.append(name)
    return tuple(seen)


def detail_resources(body: str) -> tuple[str, ...]:
    """Resources the breaking rows apply to, by their object name.

    `Checkout.Session.collected_information` -> `Session`,
    `PromotionCode#create` -> `PromotionCode`: the last CapitalCase part.
    """
    seen: list[str] = []
    for fields, resources in _breaking_rows(body):
        for text in resources:
            caps = [p for p in re.split(r"[.#]", text) if p[:1].isupper()]
            if caps and caps[-1] not in seen:
                seen.append(caps[-1])
    return tuple(seen)
    for sym in extract_symbols(body):
        name = sym.split(".")[-1]
        if "_" in name and name.islower() and name not in seen:
            seen.append(name)
    return tuple(seen)


_SDK_SECTION_RE = re.compile(r"^####\s+(?!REST API\s*$).+?$.*?(?=^#{2,4}\s|\Z)", re.MULTILINE | re.DOTALL)
_UPGRADE_RE = re.compile(r"^## Upgrade\s*$.*", re.MULTILINE | re.DOTALL)


def _prose_and_rest_changes(body: str) -> str:
    """Drop per-SDK copies of the changes table and the generic upgrade steps.

    Detail pages repeat the REST changes table once per SDK (Ruby, Java,
    Go, ...) and end with boilerplate upgrade steps; left in, they bury the
    prose that says what the new shape is (e.g. "not expanded in events").
    """
    return _SDK_SECTION_RE.sub("", _UPGRADE_RE.sub("", body))


def enrich_change(change, fetch=None):
    """Fetch the entry's detail page for a fuller description.

    Table-format changelog entries carry only their title; the linked .md
    detail page has the full prose (including replacement guidance the patch
    agent needs). Current titles are plain prose naming no fields, so a
    change without symbols takes them from the detail page (see
    detail_symbols); symbols from the title are kept as-is. Line structure is preserved so code samples in the guidance
    stay readable. Failure-tolerant: any fetch problem returns the change
    as-is, with a warning — the patch will be lower-quality without it.
    """
    if not change.url.endswith(".md"):
        return change
    if fetch is None:
        from apiwatch.watcher.core import load_source
        fetch = load_source
    try:
        body = fetch(change.url)
    except Exception as exc:
        print(f"[apiwatch] WARNING: could not fetch change detail {change.url}: {exc}; "
              "patching from the headline only")
        return change
    tidy = "\n".join(line.rstrip() for line in _prose_and_rest_changes(body).splitlines())
    description = re.sub(r"\n{3,}", "\n\n", tidy).strip()[:_DETAIL_CAP]
    if not description:
        return change
    if change.symbols:
        return replace(change, description=description)
    return replace(change, description=description, symbols=detail_symbols(body),
                   resources=detail_resources(body))


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
