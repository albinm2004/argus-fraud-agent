"""Argus -- Razorpay webhook receiver (FastAPI).

A real HTTP service, not just a script -- point Razorpay's webhook
dashboard at this (via ngrok or similar for local testing) and it
verifies the HMAC signature exactly as agents/watcher.py does, normalizes
the event, and -- if the transaction happens to match one in the demo
feature store (see the scope note below) -- runs it through the full
Argus pipeline and returns a real verdict.

Honest scope boundary, same one documented in agents/pipeline.py: turning
ANY raw webhook payload into the full engineered feature vector needs a
live feature store built from transaction history, which is out of scope
for this build. This receiver stands in with a static in-memory lookup
built from the held-out IEEE-CIS test set, purely so there's something
end-to-end to point a real webhook at. Genuine live Razorpay traffic
(e.g. a real test payment forwarded via ngrok) will correctly verify its
signature and get normalized -- that part is fully real -- but will get
a 202 "no feature vector available" instead of a fabricated verdict.
That's the honest behavior, not a bug: this project doesn't pretend to
solve real-time feature engineering it didn't build.

Run:    PYTHONPATH=. uvicorn app.webhook_receiver:app --reload --port 8000
Health: curl http://localhost:8000/health
Tests:  tests/test_webhook_receiver.py (uses FastAPI's TestClient, no
        network or running server needed)
"""
import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agents.pipeline import investigate
from agents.watcher import normalize_event, verify_signature

logger = logging.getLogger("argus.webhook_receiver")

app = FastAPI(title="Argus Webhook Receiver")

_feature_store: Optional[dict] = None  # lazy-loaded, see _load_feature_store()


def _load_feature_store() -> dict:
    """Loads the held-out test set once per process and indexes it by
    TransactionID. Stands in for a real feature store -- see the module
    docstring's scope note. Loaded lazily (not at import time) so tests
    that don't touch this endpoint, and `uvicorn --reload`'s first
    import, don't pay the ~1 minute dataset-load cost."""
    global _feature_store
    if _feature_store is None:
        from agents.features import build_dataset
        df, _, split_idx = build_dataset()
        test_df = df.iloc[split_idx:]
        _feature_store = {int(row["TransactionID"]): row for _, row in test_df.iterrows()}
        logger.info("Feature store loaded: %d demo transactions indexed", len(_feature_store))
    return _feature_store


@app.get("/health")
def health():
    return {"status": "ok", "service": "argus-webhook-receiver"}


@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(default=None),
):
    body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=401, detail="Missing X-Razorpay-Signature header")

    try:
        valid = verify_signature(body, x_razorpay_signature)
    except ValueError as e:
        # No webhook secret configured on this server -- a deploy/config
        # problem, not a bad request, so 500 rather than 401.
        raise HTTPException(status_code=500, detail=str(e))

    if not valid:
        logger.warning("Rejected webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        raw_event = await request.json()
        normalized = normalize_event(raw_event)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed payload: {e}")

    logger.info("Verified webhook: txn_id=%s amount=%s", normalized["txn_id"], normalized["amount"])

    try:
        txn_id = int(normalized["txn_id"])
    except (TypeError, ValueError):
        txn_id = None

    store = _load_feature_store()
    if txn_id is not None and txn_id in store:
        result = investigate(txn_id, store[txn_id], run_red_team=False)
        v = result["verdict_result"]
        return JSONResponse(status_code=200, content={
            "received": True,
            "scored": True,
            "txn_id": txn_id,
            "verdict": v["verdict"],
            "score": v["score"],
            "threshold": v["threshold"],
            "evidence": v["evidence"],
        })

    return JSONResponse(status_code=202, content={
        "received": True,
        "scored": False,
        "txn_id": txn_id,
        "reason": (
            "Signature verified and event normalized, but no feature vector is "
            "available for this transaction -- this demo's feature store only "
            "covers the held-out IEEE-CIS test set, not arbitrary live traffic. "
            "A production deployment needs a real-time feature store built from "
            "transaction history; see the scope note in agents/pipeline.py."
        ),
    })
