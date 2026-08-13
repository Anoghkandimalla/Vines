from pathlib import Path

from apiwatch.watcher.stripe import extract_symbols, parse_changelog

FIXTURE = Path(__file__).parent / "fixtures" / "stripe_changelog.md"


def test_extract_symbols_dedupes_in_order():
    assert extract_symbols("The `charges` prop; use `latest_charge`; not `charges` again") == (
        "charges",
        "latest_charge",
    )


def test_parse_finds_all_versions():
    entries = parse_changelog(FIXTURE.read_text())
    assert [e.version for e in entries][:2] == ["2022-11-15", "2022-11-15"]
    versions = {e.version for e in entries}
    assert versions == {"2022-11-15", "2022-08-01", "2020-08-27"}


def test_parse_marks_breaking_and_symbols():
    entries = parse_changelog(FIXTURE.read_text(), url="https://docs.stripe.com/upgrades")
    charges = [e for e in entries if "charges" in e.symbols and e.version == "2022-11-15"]
    assert len(charges) == 1
    e = charges[0]
    assert e.breaking is True
    assert e.api == "stripe"
    assert "latest_charge" in e.symbols
    assert "PaymentIntent" in e.symbols
    assert e.url == "https://docs.stripe.com/upgrades#2022-11-15"


def test_non_breaking_entries_flagged():
    entries = parse_changelog(FIXTURE.read_text())
    other = [e for e in entries if e.version == "2022-11-15" and not e.breaking]
    assert len(other) == 1
    assert "Account" in other[0].symbols


INDEX_FIXTURE = Path(__file__).parent / "fixtures" / "stripe_changelog_index.md"


def test_parse_table_format_versions_including_suffixed():
    entries = parse_changelog(INDEX_FIXTURE.read_text())
    versions = {e.version for e in entries}
    assert "2026-07-29.dahlia" in versions
    assert "2022-11-15" in versions
    assert "2022-08-01" in versions


def test_parse_table_format_breaking_flag_from_column():
    entries = parse_changelog(INDEX_FIXTURE.read_text())
    dahlia = [e for e in entries if e.version == "2026-07-29.dahlia"]
    assert dahlia and all(not e.breaking for e in dahlia)
    v2211 = [e for e in entries if e.version == "2022-11-15"]
    assert len(v2211) == 5 and all(e.breaking for e in v2211)


def test_parse_table_format_charges_removal_entry():
    entries = parse_changelog(INDEX_FIXTURE.read_text())
    hits = [e for e in entries if "charges" in e.symbols and e.version == "2022-11-15"]
    assert len(hits) == 1
    e = hits[0]
    assert e.breaking is True
    assert "PaymentIntent" in e.symbols
    assert e.url == "https://docs.stripe.com/changelog/2022-11-15/removes-charges-attribute-paymentintent.md"
