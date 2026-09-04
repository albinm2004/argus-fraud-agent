"""Loads the held-out test-set transactions into the real Neo4j AuraDB
instance (not the full 590K-row dataset -- Aura's Free tier caps out
around 200K nodes / 400K relationships, and the held-out set at ~118K
transactions plus its card/addr entities comfortably fits with room to
spare, while still being large enough to demo real ring detection).

Run (from repo root, needs .env configured and real internet access --
this will NOT work from a sandboxed dev shell with restricted egress,
run it from your own terminal):
    PYTHONPATH=. python scripts/load_graph_to_neo4j.py
"""
import sys
import time

from agents.features import load_raw
from agents.graph_builder_neo4j import check_connection, write_transactions_batch, get_driver, close_driver

BATCH_SIZE = 1000


def main():
    print("Checking Neo4j connection...")
    if not check_connection():
        print("Could not connect to Neo4j. Check .env (NEO4J_URI/USERNAME/PASSWORD) "
              "and that this machine has real internet access.")
        close_driver()  # opened by check_connection() above -- close it before exiting
        sys.exit(1)
    print("Connected.")

    df = load_raw()
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:]  # same held-out split as training
    print(f"Loading {len(test_df):,} held-out transactions into Neo4j "
          f"(batches of {BATCH_SIZE})...")

    t0 = time.time()
    rows = []
    for i, row in enumerate(test_df.itertuples(index=False), 1):
        rows.append({
            "txn_id": str(row.TransactionID),
            "card1": str(row.card1) if row.card1 == row.card1 else None,  # NaN check
            "addr1": str(row.addr1) if row.addr1 == row.addr1 else None,
            "is_fraud": bool(row.isFraud),
        })
        if len(rows) >= BATCH_SIZE:
            write_transactions_batch(rows)
            rows = []
            if i % 10000 == 0:
                print(f"  {i:,}/{len(test_df):,} ({time.time()-t0:.0f}s elapsed)")
    if rows:
        write_transactions_batch(rows)

    print(f"Done in {time.time()-t0:.0f}s.")

    with get_driver().session() as s:
        counts = s.run(
            "MATCH (t:Transaction) WITH count(t) AS txns "
            "MATCH (c:Card) WITH txns, count(c) AS cards "
            "MATCH (a:Addr) RETURN txns, cards, count(a) AS addrs"
        ).single()
        print(f"Graph now holds: {counts['txns']:,} transactions, "
              f"{counts['cards']:,} cards, {counts['addrs']:,} addresses.")

    # Short-lived script -- close explicitly so the interpreter doesn't tear
    # the driver's socket down mid-flight on exit (see close_driver()'s
    # docstring in agents/graph_builder_neo4j.py for why that prints a
    # scary-looking "Failed to write data to connection ..." warning).
    close_driver()


if __name__ == "__main__":
    main()
