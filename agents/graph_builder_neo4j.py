"""Graph Builder Agent — Neo4j-backed implementation.

Schema: (Transaction {id, is_fraud})-[:USES_CARD]->(Card {value})
        (Transaction)-[:USES_ADDR]->(Addr {value})

Ring detection here is bounded-hop (2 hops: txn -> entity -> other txns
sharing that entity), not full connected-component search — AuraDB's Free
tier doesn't include the Graph Data Science library that connected-component
algorithms need, and unbounded traversal isn't something you want in a
live scoring path anyway. This trades some recall on deep, indirect rings
for a query that's fast and actually runs on the free tier.
"""
from contextlib import contextmanager

from neo4j import GraphDatabase

from config import settings

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _driver


@contextmanager
def session():
    driver = get_driver()
    s = driver.session(database=settings.neo4j_database or None)
    try:
        yield s
    finally:
        s.close()


def check_connection(timeout_s: float = 5.0) -> bool:
    try:
        with session() as s:
            return s.run("RETURN 1 AS ok").single()["ok"] == 1
    except Exception:
        return False


def write_transactions_batch(rows: list[dict]):
    """rows: [{"txn_id":..., "card1":..., "addr1":..., "is_fraud":...}, ...]
    Uses UNWIND for one round-trip per batch instead of one query per row —
    matters once you're writing more than a handful of transactions over
    a network connection to Aura."""
    query = """
    UNWIND $rows AS row
    MERGE (t:Transaction {id: row.txn_id})
    SET t.is_fraud = row.is_fraud
    WITH t, row
    FOREACH (_ IN CASE WHEN row.card1 IS NOT NULL THEN [1] ELSE [] END |
        MERGE (c:Card {value: row.card1})
        MERGE (t)-[:USES_CARD]->(c)
    )
    FOREACH (_ IN CASE WHEN row.addr1 IS NOT NULL THEN [1] ELSE [] END |
        MERGE (a:Addr {value: row.addr1})
        MERGE (t)-[:USES_ADDR]->(a)
    )
    """
    with session() as s:
        s.run(query, rows=rows)


def get_graph_features(txn_id) -> dict:
    query = """
    MATCH (t:Transaction {id: $txn_id})
    OPTIONAL MATCH (t)-[:USES_CARD]->(:Card)<-[:USES_CARD]-(shared_card:Transaction)
    OPTIONAL MATCH (t)-[:USES_ADDR]->(:Addr)<-[:USES_ADDR]-(shared_addr:Transaction)
    WITH t,
         count(DISTINCT shared_card) AS shared_card_count,
         count(DISTINCT shared_addr) AS shared_addr_count,
         collect(DISTINCT shared_card) + collect(DISTINCT shared_addr) AS neighbors
    RETURN t.is_fraud AS found,
           shared_card_count,
           shared_addr_count,
           size([n IN neighbors WHERE n.is_fraud]) AS neighbor_fraud_count,
           size(neighbors) AS neighbor_count
    """
    with session() as s:
        record = s.run(query, txn_id=str(int(float(txn_id)))).single()
        if record is None:
            return {"found": False}
        return {
            "found": True,
            "shared_card_count": record["shared_card_count"],
            "shared_addr_count": record["shared_addr_count"],
            "neighbor_count": record["neighbor_count"],
            "neighbor_fraud_count": record["neighbor_fraud_count"],
        }
