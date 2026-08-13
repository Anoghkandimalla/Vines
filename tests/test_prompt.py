from apiwatch.models import CallSite, ChangeEntry
from apiwatch.patcher.prompt import build_prompt


def _change():
    return ChangeEntry(
        api="stripe",
        version="2022-11-15",
        title="charges removed",
        description="The `charges` property on `PaymentIntent` is no longer included by default. Use `latest_charge`.",
        breaking=True,
        symbols=("charges", "PaymentIntent", "latest_charge"),
        url="https://docs.stripe.com/upgrades#2022-11-15",
    )


def test_prompt_contains_change_and_sites():
    sites = [CallSite("app.py", 2, "charge = pi.charges.data[0]", "charges")]
    p = build_prompt(_change(), sites)
    assert "stripe" in p
    assert "2022-11-15" in p
    assert "https://docs.stripe.com/upgrades#2022-11-15" in p
    assert "app.py:2" in p
    assert "charge = pi.charges.data[0]" in p


def test_prompt_constrains_agent():
    p = build_prompt(_change(), [CallSite("app.py", 2, "x", "charges")])
    assert "only" in p.lower()
    assert "do not" in p.lower()
