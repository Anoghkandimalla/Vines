"""Build the instruction handed to the coding agent."""
from typing import Sequence

from apiwatch.models import CallSite, ChangeEntry


def build_prompt(change: ChangeEntry, sites: list[CallSite], fixtures: Sequence[str] = ()) -> str:
    site_lines = "\n".join(f"- {s.file}:{s.line}  `{s.snippet}`" for s in sites)
    files = sorted({s.file for s in sites} | set(fixtures))
    fixture_section = ""
    if fixtures:
        fixture_lines = "\n".join(f"- {f}" for f in fixtures)
        fixture_section = f"""
## Test fixtures that may record the old shape

{fixture_lines}

If your patched code still handles the old shape, leave these as they are:
they keep covering the old-version path, and the tests asserting on them
still pass. Update a fixture only where your change drops support for the
shape it records.
"""
    return f"""You are patching this repository for a breaking change in the {change.api} API.

## The breaking change ({change.api} API version {change.version})

{change.description}

Changelog: {change.url}

## Affected call sites found in this repo

{site_lines}
{fixture_section}
## Your task

Edit the affected code so it works correctly with {change.api} API version {change.version}.

Before editing, work out from the change description exactly what the new
response or request looks like: for every field the affected code reads or
sends, state its location and type (object, ID string, list, ...) in the new
version, quoting the sentence of the description that says so. Then follow
the vendor's stated replacement:
- A field that is no longer expanded arrives as an ID string, not an object;
  code reading its attributes must fetch or expand it explicitly (as the
  changelog describes) or stop depending on them.
- Moved or renamed fields must be read from their new location, with the new
  type the changelog gives.
- Never invent a path to data the new version no longer returns. If it is
  gone, use the replacement the changelog names, or degrade gracefully.
- Code that receives payloads it did not request (e.g. webhooks) may see both
  old and new API versions; keep handling the old shape as well.

Rules:
- Only edit these files: {", ".join(files)}.
- Make the minimal change required; do not reformat, rename, or refactor unrelated code.
- Do not add new dependencies.
- Do not create, delete, or move files.
- Preserve existing behavior for everything the breaking change does not affect.
"""
