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
    assert "feature_store_loaded" in resp.json()


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
    """A genuinely live transaction (not in our demo dataset, or not
    scoreable because the demo dataset isn't even present on this
    deployment -- see the feature-store try/except) should still verify
    and normalize correctly. It just can't be scored, and says so
    honestly with a 202 instead of faking a verdict or crashing with a
    500 (the bug this test guards against: an earlier version called
    _load_feature_store() unconditionally with no error handling, so on
    a deployment without the IEEE-CIS dataset baked in, EVERY valid
    webhook -- not just unknown ones -- would 500)."""
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


def test_duplicate_delivery_is_acknowledged_without_reprocessing(client):
    """Razorpay (like most webhook providers) can redeliver the same
    event -- e.g. on a retry after a slow response. A second delivery of
    the identical signed payload should be acknowledged (200) without
    being scored/logged again."""
    body = _payload(txn_id=42424242)
    raw = json.dumps(body).encode()
    signature = _sign(raw)
    headers = {"X-Razorpay-Signature": signature}

    first = client.post("/webhooks/razorpay", content=raw, headers=headers)
    assert first.status_code in (200, 202)
    assert first.json().get("duplicate") is not True

    second = client.post("/webhooks/razorpay", content=raw, headers=headers)
    assert second.status_code == 200
    data = second.json()
    assert data["duplicate"] is True
    # txn_id in the response is Razorpay's raw payment id (a string) --
    # see test_duplicate_delivery_uses_real_razorpay_id_not_just_numeric_demo_ids
    # for why this can't be int(...)'d.
    assert data["txn_id"] == "42424242"


def test_duplicate_delivery_uses_real_razorpay_id_not_just_numeric_demo_ids(client):
    """Regression test for a real bug: dedup used to key off int(payment
    id), but a genuine Razorpay payment id (e.g. "pay_MnFHJ1n5AwvSxE") is
    never a bare integer, so int() always raised and replay protection
    silently never engaged for real traffic -- only for this test suite's
    own numeric-string demo ids. This uses a realistic non-numeric id to
    make sure dedup still works for it."""
    body = _payload(txn_id=1)
    body["payload"]["payment"]["entity"]["id"] = "pay_MnFHJ1n5AwvSxE"
    raw = json.dumps(body).encode()
    signature = _sign(raw)
    headers = {"X-Razorpay-Signature": signature}

    first = client.post("/webhooks/razorpay", content=raw, headers=headers)
    assert first.status_code in (200, 202)
    assert first.json().get("duplicate") is not True
    assert first.json()["txn_id"] == "pay_MnFHJ1n5AwvSxE"

    second = client.post("/webhooks/razorpay", content=raw, headers=headers)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["txn_id"] == "pay_MnFHJ1n5AwvSxE"


def test_concurrent_duplicate_deliveries_only_process_once(client):
    """Regression test for a real race condition: the dedup check ("is
    this id already processed?") and the reservation (add it to the
    processed set) used to be two separate, unlocked steps, so two
    near-simultaneous deliveries of the same event -- which Razorpay's
    own retry behavior can genuinely produce -- could both pass the
    check before either finished the add, and both would get scored/
    logged. Found by firing 10+ concurrent identical requests at the
    endpoint with real threads and seeing all of them come back
    non-duplicate instead of exactly one. Fixed with a lock around the
    check-and-reserve step; this test fires real concurrent requests
    (not just sequential calls) to make sure exactly one wins."""
    import threading

    body = _payload(txn_id=13131313)
    raw = json.dumps(body).encode()
    signature = _sign(raw)
    headers = {"X-Razorpay-Signature": signature}

    results = []
    results_lock = threading.Lock()

    def fire():
        resp = client.post("/webhooks/razorpay", content=raw, headers=headers)
        with results_lock:
            results.append(resp.json().get("duplicate"))

    threads = [threading.Thread(target=fire) for _ in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    non_duplicate_count = sum(1 for d in results if d is not True)
    assert non_duplicate_count == 1, (
        f"expected exactly 1 of 15 concurrent identical deliveries to be the "
        f"non-duplicate winner, got {non_duplicate_count} -- dedup race reintroduced"
    )


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
