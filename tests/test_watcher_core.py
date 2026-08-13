from apiwatch.models import ChangeEntry
from apiwatch.watcher.core import html_to_text, load_source, new_breaking_changes


def _e(version, breaking=True):
    return ChangeEntry("stripe", version, "t", "d", breaking, (), "")


def test_new_breaking_filters_by_version_and_breaking():
    entries = [_e("2022-11-15"), _e("2022-11-15", breaking=False), _e("2022-08-01"), _e("2020-08-27")]
    got = new_breaking_changes(entries, "2022-08-01")
    assert [e.version for e in got] == ["2022-11-15"]
    assert all(e.breaking for e in got)


def test_new_breaking_none_state_returns_all_breaking():
    entries = [_e("2022-11-15"), _e("2020-08-27", breaking=False)]
    assert len(new_breaking_changes(entries, None)) == 1


def test_load_source_reads_file(tmp_path):
    f = tmp_path / "log.md"
    f.write_text("## 2022-11-15\n")
    assert load_source(str(f)) == "## 2022-11-15\n"


def test_html_to_text_converts_structure():
    html = "<h2>2022-11-15</h2><h3>Breaking changes</h3><ul><li>The <code>charges</code> property.</li></ul>"
    text = html_to_text(html)
    assert "## 2022-11-15" in text
    assert "### Breaking changes" in text
    assert "- The `charges` property." in text
