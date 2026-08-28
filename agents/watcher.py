"""Watcher Agent — ingests Razorpay test-mode transaction events.

TODO (Day 1-2):
- Wire up a Razorpay webhook receiver (Orders + Payment Links events).
- Verify webhook signatures using RAZORPAY_WEBHOOK_SECRET.
- Normalize each event into a flat transaction record:
    {txn_id, amount, card_fingerprint, device_id, ip, user_id,
     merchant_id, timestamp}
- Hand normalized records to the Graph Builder.
"""


def normalize_event(raw_event: dict) -> dict:
    """Convert a raw Razorpay webhook payload into a transaction record."""
    raise NotImplementedError
