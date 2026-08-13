"""Order fulfillment using Stripe. Written against Stripe API 2022-08-01."""
import stripe


def get_receipt_url(payment_intent_id: str) -> str | None:
    pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    charges = pi.charges.data
    if not charges:
        return None
    return charges[0].receipt_url


def was_paid(payment_intent_id: str) -> bool:
    pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    return any(c.status == "succeeded" for c in pi.charges.data)
