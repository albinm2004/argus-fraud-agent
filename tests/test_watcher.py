"""Watcher agent: signature verification and event normalization are pure
functions (no network needed), so they're fully unit-testable."""
import hashlib
import hmac

import pytest

from agents.watcher import normalize_event, verify_signature


def test_verify_signature_accepts_valid():
    secret = "whsec_test123"
    body = b'{"event": "payment.captured"}'
    sig = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, secret) is True


def test_verify_signature_rejects_tampered_body():
    secret = "whsec_test123"
    body = b'{"event": "payment.captured"}'
    sig = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    tampered_body = b'{"event": "payment.captured", "amount": 999999}'
    assert verify_signature(tampered_body, sig, secret) is False


def test_verify_signature_rejects_wrong_secret():
    body = b'{"event": "payment.captured"}'
    sig = hmac.new(b"whsec_correct", msg=body, digestmod=hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, "whsec_wrong") is False


def test_verify_signature_raises_without_secret():
    with pytest.raises(ValueError):
        verify_signature(b"{}", "deadbeef", secret=None)


SAMPLE_WEBHOOK = {
    "entity": "event",
    "event": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test123",
                "amount": 150000,
                "currency": "INR",
                "status": "captured",
                "order_id": "order_test123",
                "method": "card",
                "card": {"network": "Visa", "type": "credit", "last4": "4242"},
                "email": "buyer@example.com",
                "contact": "+911234567890",
                "notes": {},
                "created_at": 1735000000,
            }
        }
    },
}


def test_normalize_event_extracts_expected_fields():
    result = normalize_event(SAMPLE_WEBHOOK)
    assert result["txn_id"] == "pay_test123"
    assert result["amount"] == 1500.0  # paise -> rupees
    assert result["card_network"] == "Visa"
    assert result["device_id"] is None  # honestly absent, not fabricated


def test_normalize_event_raises_on_missing_payment():
    with pytest.raises(ValueError):
        normalize_event({"event": "payment.captured", "payload": {}})
