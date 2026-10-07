"""Parse Twilio's release changelog into structured entries.

Twilio publishes API changes through its helper libraries' CHANGES.md (e.g.
https://raw.githubusercontent.com/twilio/twilio-python/main/CHANGES.md):
one `[YYYY-MM-DD] Version x.y.z` heading per release, `**Product**` lines
grouping bullets, and breaking bullets tagged `**(breaking change)**`.

Twilio's changelog names REST parameters in PascalCase/camelCase (`SinkSid`,
`speechModel`) while the Python helper library exposes them in snake_case
(`sink_sid`, `speech_model`), so symbols carry both spellings. Bare
snake_case words (`sms_pumping_risk` without backticks) count too, since
Twilio often leaves field names unquoted.
"""
import re

from apiwatch.models import ChangeEntry

_RELEASE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s+Version\s+(\S+)\s*$")
_PRODUCT_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
_BREAKING_RE = re.compile(r"\s*\*\*\(breaking change\)\*\*\s*", re.IGNORECASE)
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")
_BARE_SNAKE_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_RAW_GITHUB_RE = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$")


def _snake(name: str) -> str:
    return _CAMEL_BOUNDARY_RE.sub("_", name).lower()


def extract_symbols(text: str) -> tuple[str, ...]:
    found = _BACKTICK_RE.findall(text) + _BARE_SNAKE_RE.findall(text)
    seen: list[str] = []
    for sym in found:
        # Single-word names (`Tags` -> `tags`) would become generic primary
        # symbols, so only multi-word names get a snake_case variant.
        snake = _snake(sym)
        for variant in (sym, snake) if "_" in snake else (sym,):
            if variant not in seen:
                seen.append(variant)
    return tuple(seen)


def _human_url(url: str) -> str:
    """Point PR links at GitHub's rendered view rather than the raw file."""
    m = _RAW_GITHUB_RE.match(url)
    return f"https://github.com/{m[1]}/{m[2]}/blob/{m[3]}/{m[4]}" if m else url


def parse_changelog(text: str, url: str = "") -> list[ChangeEntry]:
    # Versions are release dates so the watermark compares as ISO strings
    # like Stripe's; two releases on one date share a watermark.
    entries: list[ChangeEntry] = []
    link = _human_url(url)
    date = release = product = None
    for line in text.splitlines():
        if m := _RELEASE_RE.match(line):
            date, release, product = m[1], m[2], None
            continue
        if date is None:
            continue
        if m := _PRODUCT_RE.match(line):
            product = m[1].strip()
            continue
        if not line.startswith("- ") or product is None:
            continue
        body = line[2:]
        breaking = bool(_BREAKING_RE.search(body))
        body = " ".join(_LINK_RE.sub(r"\1", _BREAKING_RE.sub(" ", body)).split())
        if not body:
            continue
        desc = f"{product} (twilio-python {release}): {body}"
        entries.append(
            ChangeEntry(
                api="twilio",
                version=date,
                title=f"{product}: {body}"[:80],
                description=desc,
                breaking=breaking,
                symbols=extract_symbols(body),
                url=link,
            )
        )
    return entries
