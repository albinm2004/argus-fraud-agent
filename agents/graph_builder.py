"""Graph Builder Agent — writes transaction entities into Neo4j.

TODO (Day 1-2):
- Connect to Neo4j AuraDB using config.settings.
- Upsert nodes: Transaction, Card, Device, IP, User, Merchant.
- Create edges for shared cards/devices/IPs across transactions/users.
- Expose a query helper for graph features (centrality, community
  membership, shared-entity counts) that the Pattern Analyst consumes.
"""


def write_transaction(record: dict) -> None:
    raise NotImplementedError


def get_graph_features(txn_id: str) -> dict:
    raise NotImplementedError
