from apiwatch.state import load_state, save_state


def test_load_missing_returns_empty(tmp_path):
    assert load_state(tmp_path / "nope" / "state.json") == {}


def test_round_trip_creates_parents(tmp_path):
    p = tmp_path / ".apiwatch" / "state.json"
    save_state(p, {"stripe": {"last_version": "2022-08-01"}})
    assert load_state(p) == {"stripe": {"last_version": "2022-08-01"}}
