"""Graph Builder Agent — builds and queries the transaction entity graph.

Bipartite graph: transaction nodes ("txn:<id>") connected to entity nodes
("card:<card1>", "addr:<addr1>") they share with other transactions. This
is what a frequency count can't give you: TRANSITIVE structure — if txn A
shares a card with txn B, and txn B shares an address with txn C, A and C
land in the same connected component even though they never directly
share anything. That's the actual value of graph reasoning over the
frequency-proxy features used for the baseline model.

Build (from repo root): PYTHONPATH=. python -c "from agents.graph_builder import build_and_save; build_and_save()"
(this is also called by scripts/build_graph.py)
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

_GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "entity_graph.gpickle"
_graph = None
_neo4j_checked = False
_neo4j_available = False


# Addresses shared by more than this many transactions are excluded as
# graph edges (not as features elsewhere). Empirically, addr1 alone
# collapses ~99% of the dataset into one giant connected component past
# a certain popularity (large fulfillment centers, shared defaults, etc.)
# -- excluding just the top ~60 hub addresses roughly quintuples the
# count of small, dense, ring-like components without losing the address
# signal for the vast majority of (non-hub) addresses. This is an honest
# tradeoff, not a full fix -- see docs/eda_findings.md.
ADDR_HUB_CAP = 200


def build_graph(df: pd.DataFrame, addr_hub_cap: int = ADDR_HUB_CAP) -> nx.Graph:
    addr_counts = df["addr1"].value_counts()
    hub_addrs = set(addr_counts[addr_counts > addr_hub_cap].index)

    G = nx.Graph()
    for row in df[["TransactionID", "card1", "addr1", "isFraud"]].itertuples(index=False):
        txn_node = f"txn:{row.TransactionID}"
        G.add_node(txn_node, kind="txn", is_fraud=bool(row.isFraud))
        if pd.notna(row.card1):
            G.add_edge(txn_node, f"card:{row.card1}")
        if pd.notna(row.addr1) and row.addr1 not in hub_addrs:
            G.add_edge(txn_node, f"addr:{row.addr1}")
    return G


def build_and_save(raw_dir="data/raw/ieee-fraud-detection"):
    from agents.features import load_raw
    df = load_raw(raw_dir)
    G = build_graph(df)
    _GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)
    return G


def _load():
    global _graph
    if _graph is None:
        if not _GRAPH_PATH.exists():
            raise FileNotFoundError(f"No graph at {_GRAPH_PATH}. Run build_and_save() first.")
        with open(_GRAPH_PATH, "rb") as f:
            _graph = pickle.load(f)
    return _graph


def _txn_key(txn_id) -> str:
    """Coerces txn_id to a clean integer string. Needed because a single
    row pulled from a mixed-dtype DataFrame (float columns present
    elsewhere) upcasts TransactionID to float -- e.g. 3459499.0 -- which
    silently fails to match the "txn:3459499" node built from the raw
    int64 column, if not normalized first."""
    return str(int(float(txn_id)))


def get_graph_features(txn_id) -> dict:
    """Tries the live Neo4j graph first (agents.graph_builder_neo4j), falls
    back to the local networkx graph if Neo4j isn't reachable or configured
    -- keeps the rest of the pipeline working even when the live graph
    database is unavailable, which matters more than it sounds like it
    should when you're demoing over conference wifi.

    Returns entity degrees, connected-component size (networkx path) or
    bounded-neighbor fraud count (Neo4j path) -- the ring-detection signal
    a frequency count alone can't produce."""
    global _neo4j_checked, _neo4j_available
    if not _neo4j_checked:
        try:
            from agents.graph_builder_neo4j import check_connection
            _neo4j_available = check_connection(timeout_s=3.0)
        except Exception:
            _neo4j_available = False
        _neo4j_checked = True

    if _neo4j_available:
        try:
            from agents.graph_builder_neo4j import get_graph_features as neo4j_features
            result = neo4j_features(txn_id)
            result["source"] = "neo4j"
            return result
        except Exception:
            pass  # fall through to local graph

    G = _load()
    txn_node = f"txn:{_txn_key(txn_id)}"
    if txn_node not in G:
        return {"found": False}

    card_degree = 0
    addr_degree = 0
    for nbr in G.neighbors(txn_node):
        if nbr.startswith("card:"):
            card_degree = G.degree(nbr) - 1  # exclude this txn itself
        elif nbr.startswith("addr:"):
            addr_degree = G.degree(nbr) - 1

    component = nx.node_connected_component(G, txn_node)
    component_txns = [n for n in component if n.startswith("txn:")]
    fraud_in_component = sum(1 for n in component_txns if G.nodes[n].get("is_fraud"))

    return {
        "found": True,
        "source": "networkx (local fallback)",
        "shared_card_count": card_degree,
        "shared_addr_count": addr_degree,
        "connected_component_size": len(component_txns),
        "other_fraud_in_component": max(0, fraud_in_component - int(G.nodes[txn_node].get("is_fraud", False))),
    }
