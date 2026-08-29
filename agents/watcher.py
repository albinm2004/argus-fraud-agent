"""Watcher Agent — ingests Razorpay test-mode transaction events.

Handles the two things that actually vary between a real payment gateway
and a Kaggle CSV: verifying the webhook really came from Razorpay, and
mapping Razorpay's payload shape onto the flat record the rest of the
pipeline (Graph Builder, Pattern Analyst) expects.

Honest limitation, not glossed over: Razorpay's payment webhooks don't
carry device fingerprint or raw IP in the standard payload -- that's
normally captured client-side at checkout (e.g. via Razorpay Checkout's
device-id metadata, passed through in `notes`) and isn't something a
server-side webhook receiver gets for free. `device_id` below is left
None unless the integrating checkout flow explicitly passes one through
notes -- it is not fabricated.
"""
import hmac
import hashlib
import json

from config import settings


def verify_signature(body: bytes, signature: str, secret: str | None = None) -> bool:
    """Razorpay signs the raw request body with HMAC-SHA256 using the
    webhook secret; the signature arrives in the X-Razorpay-Signature
    header. This is pure HMAC -- no network call, no live keys needed to
    verify correctness (only to *receive* a real webhook in the first
    place)."""
    secret = secret or settings.razorpay_webhook_secret
    if not secret:
        raise ValueError("No webhook secret configured (RAZORPAY_WEBHOOK_SECRET in .env)")
    expected = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def normalize_event(raw_event: dict) -> dict:
    """raw_event: the parsed JSON body of a Razorpay `payment.captured` /
    `payment.failed` webhook. Returns the flat record shape the rest of
    the pipeline expects (subset of features.py's TX_COLS-compatible
    fields -- this is the LIVE-signal analog of a transaction row, not a
    full feature vector; feature engineering still runs downstream)."""
    event_type = raw_event.get("event", "")
    payload = raw_event.get("payload", {})
    payment = payload.get("payment", {}).get("entity", {})

    if not payment:
        raise ValueError(f"No payment entity in webhook payload (event={event_type})")

    card = payment.get("card") or {}
    notes = payment.get("notes") or {}

    return {
        "txn_id": payment.get("id"),
        "event_type": event_type,
        "order_id": payment.get("order_id"),
        "amount": payment.get("amount", 0) / 100,  # Razorpay amounts are in paise
        "currency": payment.get("currency"),
        "status": payment.get("status"),
        "method": payment.get("method"),
        "card_network": card.get("network"),
        "card_type": card.get("type"),
        "card_last4": card.get("last4"),
        "email": payment.get("email"),
        "contact": payment.get("contact"),
        "device_id": notes.get("device_id"),  # only present if checkout flow passes it through
        "created_at": payment.get("created_at"),
    }
