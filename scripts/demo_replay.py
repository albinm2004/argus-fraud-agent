"""Demo Replay — end-to-end walkthrough: a Razorpay-shaped webhook, verified
and normalized by the real Watcher agent, run through the real LangGraph
pipeline (Graph Builder -> Pattern Analyst -> Red-Team -> Verdict), against
held-out IEEE-CIS transactions Argus has never trained on.

This is NOT a mocked pipeline -- every agent it calls is the real one:
agents/watcher.py verifies an HMAC signature exactly like it would for a
live Razorpay webhook, and agents/pipeline.py runs the actual compiled
LangGraph StateGraph, against the actual trained (hardened) model and the
actual graph (Neo4j if reachable, networkx fallback otherwise).

What IS simulated, and said out loud rather than hidden: turning a raw
webhook payload into the full ~60-column feature vector the model expects
needs a live feature store built from transaction history (see the scope
note in agents/pipeline.py) -- that's out of scope for this build. Here,
after the webhook is verified and normalized, the matching held-out row's
already-engineered features stand in for what a feature store would
return. The webhook itself, and everything after feature lookup, is real.

Usage (from repo root):
    PYTHONPATH=. python scripts/demo_replay.py
    PYTHONPATH=. python scripts/demo_replay.py --n-fraud 2 --n-legit 2 --seed 7
"""
import argparse
import hashlib
import hmac
import json
import time

from agents.features import build_dataset
from agents.pipeline import investigate
from agents.watcher import normalize_event, verify_signature
from config import settings

DEMO_WEBHOOK_SECRET = "demo_local_secret_not_from_env"

CARD_NETWORKS = {0: "Visa", 1: "Mastercard", 2: "American Express", 3: "Discover"}


def _build_webhook_payload(row) -> dict:
    """Shapes one held-out transaction as a Razorpay `payment.captured`
    webhook body. Field values not present in the IEEE-CIS dataset (email,
    contact, card last4) are plausible demo placeholders, not real PII --
    the dataset itself doesn't carry raw card/email strings, only encoded
    categoricals, so nothing here could be de-anonymized data even by
    accident."""
    txn_id = int(row["TransactionID"])
    amount_rupees = float(row["TransactionAmt"])
    created_at = int(time.time())

    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": str(txn_id),
                    "order_id": f"order_demo_{txn_id}",
                    "amount": int(round(amount_rupees * 100)),  # Razorpay amounts are paise
                    "currency": "INR",
                    "status": "captured",
                    "method": "card",
                    "card": {
                        "network": CARD_NETWORKS.get(int(row.get("card4", -1)), "Unknown"),
                        "type": "credit" if int(row.get("card6", -1)) == 0 else "debit",
                        "last4": f"{txn_id % 10000:04d}",
                    },
                    "email": "demo.customer@example.com",
                    "contact": "+919900000000",
                    "notes": {},  # honest gap: no device_id unless checkout passes one
                    "created_at": created_at,
                }
            }
        },
    }


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()


def _run_one(row, run_red_team: bool, secret: str, label: str):
    txn_id = int(row["TransactionID"])
    payload = _build_webhook_payload(row)
    body = json.dumps(payload).encode()
    signature = _sign(body, secret)

    print(f"\n{'=' * 72}\n[{label}] TransactionID={txn_id}  (true label: "
          f"{'FRAUD' if row['isFraud'] else 'legit'} -- Argus never sees this)\n{'=' * 72}")

    # 1. Watcher: real signature verification, exactly as it would run for
    #    a live Razorpay webhook receiver.
    ok = verify_signature(body, signature, secret=secret)
    print(f"  Watcher.verify_signature -> {ok}")
    assert ok, "signature should verify -- we just signed this body ourselves"

    tampered = body.replace(b'"captured"', b'"tampered"', 1)
    tampered_ok = verify_signature(tampered, signature, secret=secret)
    print(f"  Watcher.verify_signature on a tampered body -> {tampered_ok} (must be False)")
    assert not tampered_ok, "tampered body must NOT verify"

    normalized = normalize_event(json.loads(body))
    print(f"  Watcher.normalize_event -> amount=Rs.{normalized['amount']:.2f}, "
          f"method={normalized['method']}, card={normalized['card_network']} "
          f"{normalized['card_type']}, device_id={normalized['device_id']!r} "
          f"(None is honest -- Razorpay webhooks don't carry it)")

    # 2. Feature-store stand-in: look up the already-engineered feature row
    #    for this same transaction (see module docstring -- this is the
    #    one simulated step).
    result = investigate(txn_id, row, run_red_team=run_red_team)

    v = result["verdict_result"]
    gf = result["graph_features"]
    print(f"\n  VERDICT: {v['verdict'].upper()}  (score={v['score']:.3f}, "
          f"threshold={v['threshold']:.3f})")
    print(f"  Graph signal ({gf.get('source', 'not found')}): "
          f"found={gf.get('found', False)}"
          + (f", shared_card={gf.get('shared_card_count')}, "
             f"shared_addr={gf.get('shared_addr_count')}" if gf.get("found") else ""))
    print("  Evidence:")
    for line in v["evidence"]:
        print(f"    - {line}")

    if run_red_team and result.get("robustness"):
        r = result["robustness"]
        print(f"  Red-team robustness check: pre={r['pre_attack_score']:.3f} -> "
              f"post={r['post_attack_score']:.3f}  evaded={r['evaded']}")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-fraud", type=int, default=2)
    parser.add_argument("--n-legit", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-red-team", action="store_true",
                         help="skip the adversarial robustness check (faster)")
    args = parser.parse_args()

    secret = settings.razorpay_webhook_secret or DEMO_WEBHOOK_SECRET
    if not settings.razorpay_webhook_secret:
        print(f"[note] RAZORPAY_WEBHOOK_SECRET isn't set in .env -- signing with a local "
              f"demo secret ({DEMO_WEBHOOK_SECRET!r}) instead. Signature verification below "
              f"is still the real HMAC check; only the secret itself is a stand-in.")

    print("Loading held-out test set (this can take a minute on first run)...")
    df, _, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]

    fraud_sample = test_df[test_df["isFraud"] == 1].sample(
        n=min(args.n_fraud, (test_df["isFraud"] == 1).sum()), random_state=args.seed)
    legit_sample = test_df[test_df["isFraud"] == 0].sample(
        n=min(args.n_legit, (test_df["isFraud"] == 0).sum()), random_state=args.seed)

    verdicts = []
    for _, row in fraud_sample.iterrows():
        result = _run_one(row, run_red_team=not args.no_red_team, secret=secret, label="FRAUD sample")
        verdicts.append((int(row["TransactionID"]), bool(row["isFraud"]), result["verdict_result"]["verdict"]))
    for _, row in legit_sample.iterrows():
        result = _run_one(row, run_red_team=not args.no_red_team, secret=secret, label="LEGIT sample")
        verdicts.append((int(row["TransactionID"]), bool(row["isFraud"]), result["verdict_result"]["verdict"]))

    print(f"\n{'=' * 72}\nSummary ({len(verdicts)} transactions replayed as live webhooks)\n{'=' * 72}")
    for txn_id, is_fraud, verdict in verdicts:
        true_label = "FRAUD" if is_fraud else "legit"
        flagged = verdict in {"block", "flag"}
        match = "correct" if (is_fraud == flagged) else "MISS"
        print(f"  txn {txn_id}: true={true_label:<6} verdict={verdict:<6} [{match}]")
    print(f"\nFull evidence chain for every verdict above is also in "
          f"data/processed/audit_log.jsonl")


if __name__ == "__main__":
    main()
