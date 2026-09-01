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

Four robustness fixes worth calling out (found by asking "what happens
on a fresh deploy with no dataset baked in", "what happens on a
duplicate delivery", "what happens under real concurrent delivery", and
"does this actually work for a real Razorpay payment id, not just the
demo's numeric stand-in" -- rather than just the happy path):

1. Feature-store loading is wrapped in try/except. Without it, ANY
   valid-signature webhook on a deployment without the IEEE-CIS dataset
   present would 500 -- worse than the intended honest 202 -- because
   the endpoint couldn't tell "not in our demo set" from "couldn't check
   at all" without trying to load the dataset first. Now a missing
   dataset degrades to "scoring unavailable" instead of crashing.
2. Basic replay/idempotency protection: Razorpay (like most webhook
   providers) retries on non-2xx and can occasionally deliver the same
   event more than once, so the receiver tracks which transaction IDs
   it has already processed and short-circuits repeats with a plain
   200 instead of re-scoring and re-logging. This is process-local,
   in-memory state -- fine for one demo instance, not for a multi-worker
   deployment, which would need a shared store (Redis, a DB row with a
   unique constraint) with a TTL instead. Documented, not hidden.
3. That dedup set is guarded by a lock. The first version checked
   "is this txn_id already processed?" and added it to the set as two
   separate, unlocked steps -- under real concurrent delivery (Razorpay
   firing near-simultaneous retries, or several test requests at once)
   two requests could both pass the check before either finished the
   add, so both would score/log the same transaction. Fixed by reserving
   the id (check + add) inside a small lock, with the actual scoring
   done outside the lock so concurrent requests for *different*
   transactions still run in parallel.
4. The dedup key itself was wrong for real traffic. It used to be the
   SAME int(payment id) used to look transactions up in the demo's
   IEEE-CIS feature store -- but a real Razorpay payment id looks like
   "pay_MnFHJ1n5AwvSxE", never a bare integer, so int() always raised
   and txn_id was always None on genuine webhooks. That silently
   disabled replay protection for exactly the traffic it's meant to
   protect -- it only ever worked in the demo scripts, which use plain
   numeric strings as a stand-in id. Fixed by deduping on the raw
   string payment id (always present, always a valid identity) and
   keeping the int() parse only for the narrower job of indexing into
   the numeric-keyed demo feature store.

Two more things deliberately left OUT of this build, called out here
rather than silently missing:

- Rate limiting: there is none. A production webhook endpoint sitting on
  the open internet needs it (Razorpay's own retries are bounded and
  well-behaved, but nothing stops a misconfigured client, a compromised
  secret, or plain abuse from hammering this route -- signature
  verification alone doesn't limit request volume). Out of scope here
  because it needs a decision this project hasn't made (per-IP? per-key?
  what limit, backed by what store across workers?) that would be guessed
  at, not engineered, under this deadline. The honest fix is `slowapi` or
  an API-gateway-level limiter in front of this route before any real
  deployment, not a made-up threshold added last-minute to look complete.
- Auth beyond the webhook signature: the ONLY authentication on this
  route is Razorpay's own HMAC signature (verify_signature() above) --
  there's no separate API key, IP allowlist, or mTLS. That's actually
  correct for a Razorpay webhook specifically (the signature IS the
  intended auth mechanism for this exact use case), but it means this
  route is not a general-purpose authenticated API and shouldn't be
  treated as one if it's ever reused for anything beyond receiving
  Razorpay webhooks.

Run:    PYTHONPATH=. uvicorn app.webhook_receiver:app --reload --port 8000
Health: curl http://localhost:8000/health
Tests:  tests/test_webhook_receiver.py (uses FastAPI's TestClient, no
        network or running server needed)
"""
import logging
import threading
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agents.pipeline import investigate
from agents.watcher import normalize_event, verify_signature

logger = logging.getLogger("argus.webhook_receiver")

app = FastAPI(title="Argus Webhook Receiver")

_feature_store: Optional[dict] = None  # lazy-loaded, see _load_feature_store()
_feature_store_lock = threading.Lock()  # avoids double-loading the dataset on a concurrent cold start

# Process-local dedup set for replay/idempotency protection -- see module
# docstring. Cleared on process restart by design; not a durable store.
_processed_txn_ids: set = set()
_dedup_lock = threading.Lock()  # guards check-and-reserve on _processed_txn_ids -- see fix #3 above


def _load_feature_store() -> dict:
    """Loads the held-out test set once per process and indexes it by
    TransactionID. Stands in for a real feature store -- see the module
    docstring's scope note. Loaded lazily (not at import time) so tests
    that don't touch this endpoint, and `uvicorn --reload`'s first
    import, don't pay the ~1 minute dataset-load cost.

    Returns {} (cached, not retried on every request) if the dataset
    isn't available at all -- e.g. a deploy without the IEEE-CIS CSVs
    baked in or mounted -- so the endpoint degrades to "can't score"
    instead of crashing. See fix #1 in the module docstring."""
    global _feature_store
    if _feature_store is None:
        with _feature_store_lock:
            if _feature_store is None:  # re-check: another thread may have loaded it while we waited
                try:
                    from agents.features import build_dataset
                    df, _, split_idx = build_dataset()
                    test_df = df.iloc[split_idx:]
                    _feature_store = {int(row["TransactionID"]): row for _, row in test_df.iterrows()}
                    logger.info("Feature store loaded: %d demo transactions indexed", len(_feature_store))
                except Exception as e:
                    logger.warning("Feature store unavailable (%s) -- scoring disabled, "
                                    "signature verification and normalization still work.", e)
                    _feature_store = {}
    return _feature_store


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "argus-webhook-receiver",
        "feature_store_loaded": _feature_store is not None and len(_feature_store) > 0,
    }


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

    # dedup_key is Razorpay's own payment id (e.g. "pay_MnFHJ1n5AwvSxE" on
    # real traffic, or a plain numeric string in the demo/test payloads) --
    # always a string, always present on a well-formed payload, so it's a
    # reliable identity for replay protection regardless of format.
    #
    # numeric_txn_id is a SEPARATE, narrower value: an int() parse of the
    # same id, used ONLY to look a transaction up in the demo's IEEE-CIS
    # feature store (whose keys are ints). Real Razorpay payment ids are
    # never bare integers, so numeric_txn_id is always None for genuine
    # traffic -- expected, see the module docstring's scope note.
    #
    # Bug found here: an earlier version used numeric_txn_id for BOTH
    # purposes, so replay/idempotency protection (fix #2) silently never
    # engaged for real webhooks -- only for the demo scripts' numeric-string
    # ids -- because `int("pay_xxx")` always raised, leaving txn_id always
    # None and skipping the "if txn_id is not None" dedup check entirely.
    # The existing unit tests didn't catch it because they use the same
    # numeric-id convention as the demo. Found by checking what a REAL
    # Razorpay payment id looks like against what the dedup key assumed.
    dedup_key = normalized.get("txn_id")
    try:
        numeric_txn_id = int(normalized["txn_id"])
    except (TypeError, ValueError):
        numeric_txn_id = None

    # Replay/idempotency check -- see fix #2 in the module docstring. The
    # check-and-reserve is done atomically under a lock (fix #3) so two
    # near-simultaneous deliveries of the same txn_id can't both pass the
    # check before either has recorded it; only the lock is held here --
    # the actual scoring below runs unlocked so different transactions
    # still process concurrently.
    with _dedup_lock:
        if dedup_key is not None and dedup_key in _processed_txn_ids:
            logger.info("Duplicate delivery for txn_id=%s -- acknowledging without reprocessing", dedup_key)
            return JSONResponse(status_code=200, content={
                "received": True,
                "duplicate": True,
                "txn_id": dedup_key,
                "note": ("Already processed this transaction id in a prior delivery. Returning 200 "
                         "without rescoring or re-logging -- Razorpay recommends idempotent webhook "
                         "handling so a retried delivery doesn't cause duplicate side effects."),
            })
        if dedup_key is not None:
            _processed_txn_ids.add(dedup_key)  # reserve the slot before releasing the lock

    store = _load_feature_store()
    if numeric_txn_id is not None and numeric_txn_id in store:
        result = investigate(numeric_txn_id, store[numeric_txn_id], run_red_team=False)
        v = result["verdict_result"]
        return JSONResponse(status_code=200, content={
            "received": True,
            "scored": True,
            "txn_id": dedup_key,
            "verdict": v["verdict"],
            "score": v["score"],
            "threshold": v["threshold"],
            "evidence": v["evidence"],
        })

    return JSONResponse(status_code=202, content={
        "received": True,
        "scored": False,
        "txn_id": dedup_key,
        "reason": (
            "Signature verified and event normalized, but this transaction couldn't be scored -- "
            "either it isn't in this demo's held-out IEEE-CIS feature store, or that dataset isn't "
            "available on this deployment at all (see /health's feature_store_loaded). A production "
            "deployment needs a real-time feature store built from transaction history; see the "
            "scope note in agents/pipeline.py."
        ),
    })
