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
