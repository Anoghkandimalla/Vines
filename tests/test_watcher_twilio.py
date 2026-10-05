from pathlib import Path

import pytest

from apiwatch.watcher import get_format, stripe, twilio
from apiwatch.watcher.twilio import extract_symbols, parse_changelog

FIXTURE = Path(__file__).parent / "fixtures" / "twilio_changelog.md"
RAW_URL = "https://raw.githubusercontent.com/twilio/twilio-python/main/CHANGES.md"


def test_extract_symbols_adds_snake_case_variants():
    assert extract_symbols("Remove `SinkSid` parameter; `speechModel` is a string") == (
        "SinkSid", "sink_sid", "speechModel", "speech_model",
    )


def test_extract_symbols_bare_snake_case_and_no_generic_single_words():
    assert extract_symbols("Change date_created field to date_time") == ("date_created", "date_time")
    assert extract_symbols("Remove `Tags` from Public Docs") == ("Tags",)


def test_parse_versions_are_release_dates():
    entries = parse_changelog(FIXTURE.read_text())
    assert {e.version for e in entries} == {"2024-02-27", "2024-02-09", "2024-01-25"}
    assert all(e.api == "twilio" for e in entries)


def test_parse_sms_pumping_risk_carrier_removal():
    entries = parse_changelog(FIXTURE.read_text(), url=RAW_URL)
    [e] = [e for e in entries if "sms_pumping_risk" in e.symbols]
    assert e.breaking is True
    assert e.version == "2024-02-09"
    assert e.symbols == ("carrier", "sms_pumping_risk", "carrier_risk_category")
    assert e.title.startswith("Lookups: Remove `carrier` field")
    assert "8.13.0" in e.description and "breaking change" not in e.description
    assert e.url == "https://github.com/twilio/twilio-python/blob/main/CHANGES.md"


def test_parse_non_breaking_and_links_stripped():
    entries = parse_changelog(FIXTURE.read_text())
    flex = [e for e in entries if "routing_properties" in e.symbols]
    assert flex and not flex[0].breaking
    pr = [e for e in entries if "PR #767" in e.title]
    assert pr and pr[0].breaking and "](" not in pr[0].description


def test_parse_ignores_preamble_and_non_twilio_text():
    assert parse_changelog("- stray bullet\n**Api**\n- another") == []


def test_get_format_defaults_to_name_and_honours_override():
    assert get_format({"name": "stripe"}) == (stripe.parse_changelog, stripe.enrich_change)
    assert get_format({"name": "sms", "format": "Twilio"}) == (twilio.parse_changelog, None)
    with pytest.raises(ValueError, match="format"):
        get_format({"name": "acme"})
