"""Run this from YOUR OWN terminal (not through the sandboxed dev shell --
Razorpay's API and Neo4j Aura are both unreachable from there due to
egress restrictions, confirmed while building this). Checks that both
external integrations are actually live before you build on top of them.

Run: PYTHONPATH=. python scripts/smoke_test_integrations.py
"""
import sys

from config import settings


def check_razorpay():
    import razorpay
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        result = client.payment.all({"count": 1})
        print(f"  [OK] Razorpay auth works. {result.get('count', 0)} payment(s) visible in test mode.")
        return True
    except Exception as e:
        print(f"  [FAIL] Razorpay: {type(e).__name__}: {e}")
        return False


def check_neo4j():
    from agents.graph_builder_neo4j import check_connection, close_driver
    try:
        if check_connection():
            print("  [OK] Neo4j AuraDB connection works.")
            return True
        print("  [FAIL] Neo4j: could not connect. Check .env and that the Aura instance is running "
              "(free instances pause after inactivity and need a minute to wake up).")
        return False
    finally:
        # This script is short-lived -- close the driver explicitly so the
        # interpreter doesn't tear its socket down mid-flight on exit, which
        # prints a "Failed to write data to connection ..." warning that
        # looks like a real failure but isn't. See close_driver()'s docstring.
        close_driver()


if __name__ == "__main__":
    print("Razorpay:")
    rzp_ok = check_razorpay()
    print("Neo4j:")
    neo4j_ok = check_neo4j()
    print()
    if rzp_ok and neo4j_ok:
        print("Both integrations live. Safe to run scripts/load_graph_to_neo4j.py next.")
    else:
        print("Fix the failing integration(s) above before proceeding.")
        sys.exit(1)
