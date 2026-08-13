from apiwatch.mapper import scan_repo


def _mkrepo(tmp_path):
    (tmp_path / "app.py").write_text(
        "pi = stripe.PaymentIntent.retrieve(pid)\n"
        "charge = pi.charges.data[0]\n"
        "print(charge.id)\n"
    )
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "billing.py").write_text("recharges = 0  # substring of another identifier must not match\n")
    skip = tmp_path / ".apiwatch"
    skip.mkdir()
    (skip / "state.py").write_text("charges = 1\n")
    (tmp_path / "notes.txt").write_text("charges everywhere\n")
    return tmp_path


def test_scan_finds_word_boundary_matches_only(tmp_path):
    repo = _mkrepo(tmp_path)
    sites = scan_repo(repo, ["charges"])
    assert len(sites) == 1
    s = sites[0]
    assert s.file == "app.py"
    assert s.line == 2
    assert s.symbol == "charges"
    assert "pi.charges.data[0]" in s.snippet


def test_scan_multiple_symbols(tmp_path):
    repo = _mkrepo(tmp_path)
    sites = scan_repo(repo, ["charges", "PaymentIntent"])
    assert {(s.line, s.symbol) for s in sites} == {(2, "charges"), (1, "PaymentIntent")}


def test_short_symbols_skipped(tmp_path):
    repo = _mkrepo(tmp_path)
    assert scan_repo(repo, ["id"]) == []
