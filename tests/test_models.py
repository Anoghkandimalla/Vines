from apiwatch.models import CallSite, ChangeEntry


def test_change_entry_fields():
    e = ChangeEntry(
        api="stripe",
        version="2022-11-15",
        title="charges removed from PaymentIntent",
        description="The `charges` property is no longer included by default.",
        breaking=True,
        symbols=("charges", "latest_charge"),
        url="https://docs.stripe.com/upgrades#2022-11-15",
    )
    assert e.breaking is True
    assert "charges" in e.symbols


def test_call_site_fields():
    c = CallSite(file="app.py", line=12, snippet="pi.charges.data[0]", symbol="charges")
    assert c.line == 12
