"""Tests for the FastAPI webhook receiver (app/webhook_receiver.py). Uses
FastAPI's TestClient -- no running server or network needed. Requires the
raw IEEE-CIS dataset and a trained model (same artifacts as
tests/test_pipeline.py); skipped otherwise so a fresh clone's other
tests still run."""
import hashlib
import hmac
import json
from pathlib import Path

import pytest

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "ieee-fraud-detection"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

requires_artifacts = pytest.mark.skipif(
    not (RAW_DIR / "train_transaction.csv").exists()
    or not (MODELS_DIR / "pattern_analyst.joblib").exists(),
    reason="requires the raw IEEE-CIS dataset and a trained model",
)

TEST_SECRET = "test_webhook_secret_for_pytest"


def _sign(body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()


def _payload(txn_id, amount_rupees=10.0) -> dict:
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": str(txn_id),
                    "order_id": f"order_test_{txn_id}",
                    "amount": int(amount_rupees * 100),
                    "currency": "INR",
                    "status": "captured",
                    "method": "card",
                    "card": {"network": "Visa", "type": "credit", "last4": "1111"},
                    "email": "test@example.com",
                    "contact": "+919900000000",
                    "notes": {},
                    "created_at": 1700000000,
                }
            }
        },
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", TEST_SECRET)
    # config.settings reads the env var at import time via os.getenv with a
    # module-level default, so patch the already-imported settings object
    # directly rather than relying on re-import order.
    from config import settings
    monkeypatch.setattr(settings, "razorpay_webhook_secret", TEST_SECRET)

    from fastapi.testclient import TestClient
    from app.webhook_receiver import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_missing_signature_header_rejected(client):
    body = _payload(txn_id=1)
    resp = client.post("/webhooks/razorpay", content=json.dumps(body))
    assert resp.status_code == 401


def test_invalid_signature_rejected(client):
    body = _payload(txn_id=1)
    raw = json.dumps(body).encode()
    resp = client.post(
        "/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": "not_a_real_signature"},
    )
    assert resp.status_code == 401


def test_valid_signature_unknown_txn_returns_202(client):
    """A genuinely live transaction (not in our demo dataset) should still
    verify and normalize correctly -- it just can't be scored, and says
    so honestly instead of faking a verdict."""
    body = _payload(txn_id=999999999999)  # not a real IEEE-CIS TransactionID
    raw = json.dumps(body).encode()
    signature = _sign(raw)
    resp = client.post(
        "/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": signature},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["scored"] is False
    assert "no feature vector" in data["reason"]


@requires_artifacts
def test_valid_signature_known_txn_returns_verdict(client):
    """A transaction that IS in the held-out demo feature store should
    run through the real pipeline and come back with an actual verdict."""
    from agents.features import build_dataset

    df, _, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]
    txn_id = int(test_df.iloc[0]["TransactionID"])

    body = _payload(txn_id=txn_id)
    raw = json.dumps(body).encode()
    signature = _sign(raw)
    resp = client.post(
        "/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": signature},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scored"] is True
    assert data["verdict"] in {"block", "flag", "allow"}
    assert len(data["evidence"]) > 0
