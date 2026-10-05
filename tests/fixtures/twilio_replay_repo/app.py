"""Signup fraud screening using Twilio Lookup v2. Written against twilio-python 8.12.0."""
import os

from twilio.rest import Client

client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def pumping_risk(phone_number: str) -> dict:
    result = client.lookups.v2.phone_numbers(phone_number).fetch(fields="sms_pumping_risk")
    return result.sms_pumping_risk


def risky_carrier(phone_number: str) -> str | None:
    """Carrier name to log alongside high SMS-pumping-risk signups."""
    risk = pumping_risk(phone_number)
    if risk["sms_pumping_risk_score"] < 60:
        return None
    return risk["carrier"]["name"]
