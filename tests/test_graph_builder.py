"""Regression test for the TransactionID dtype bug found while wiring the
LangGraph pipeline: a single row pulled from a mixed-dtype DataFrame
upcasts TransactionID to float (e.g. 3459499.0), which used to silently
break every graph lookup by formatting as "txn:3459499.0" instead of
"txn:3459499"."""
from agents.graph_builder import _txn_key


def test_txn_key_normalizes_float_string():
    assert _txn_key(3459499.0) == "3459499"


def test_txn_key_normalizes_int():
    assert _txn_key(3459499) == "3459499"


def test_txn_key_normalizes_string_int():
    assert _txn_key("3459499") == "3459499"


def test_txn_key_normalizes_numpy_float():
    import numpy as np
    assert _txn_key(np.float64(3459499.0)) == "3459499"


def test_build_graph_excludes_hub_cards_not_just_hub_addresses():
    """Regression test for a giant-component bug found via end-to-end
    demo (scripts/demo_replay.py): the local graph capped hub addresses
    but not hub cards, so one popular card1 value silently collapsed
    ~46% of the real dataset into a single fake "ring". Here, a card
    shared by more transactions than CARD_HUB_CAP must not connect them
    into one component, while a normal (non-hub) card still should."""
    import pandas as pd
    from agents.graph_builder import build_graph, CARD_HUB_CAP

    n_hub_txns = CARD_HUB_CAP + 20
    rows = []
    for i in range(n_hub_txns):
        rows.append({"TransactionID": i, "card1": 999, "addr1": None, "isFraud": 0})
    # one normal pair that SHOULD stay linked
    rows.append({"TransactionID": 9001, "card1": 111, "addr1": None, "isFraud": 0})
    rows.append({"TransactionID": 9002, "card1": 111, "addr1": None, "isFraud": 0})
    df = pd.DataFrame(rows)

    G = build_graph(df, addr_hub_cap=200, card_hub_cap=CARD_HUB_CAP)

    # hub-card transactions must NOT be connected to each other via card:999
    assert "card:999" not in G, "hub card should be excluded as an edge entirely"
    assert not G.has_edge("txn:0", "txn:1"), "hub card must not link transactions"

    # the normal, non-hub card pair should still be linked
    import networkx as nx
    assert nx.has_path(G, "txn:9001", "txn:9002"), "non-hub shared card should still link"
