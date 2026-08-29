"""Argus — LangGraph orchestration.

Wires the five-agent pipeline as an actual StateGraph, not just
individually-callable functions: Graph Builder -> Pattern Analyst ->
[Red-Team, conditional] -> Verdict + Audit.

Scope boundary, stated plainly: this operates on an already-ENGINEERED
feature row (the same shape agents.features.build_dataset produces), not
a raw Razorpay webhook payload directly. The Watcher agent's real job --
signature verification and payload normalization (agents/watcher.py,
tested independently) -- stops at Razorpay's raw payload fields (amount,
card network, email...); turning that into the full feature vector the
trained model expects (C1-C14 velocity signals, D1-D15 time-deltas, graph-
proxy frequencies) needs an aggregated feature store built from
transaction HISTORY, which is a real, separate engineering problem this
project doesn't solve in this timeframe. Documented here rather than
papered over with a fake mapping.
"""
from typing import Optional, TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph

from agents.graph_builder import get_graph_features
from agents.pattern_analyst import score_transaction
from agents.red_team import evaluate_robustness
from agents.verdict import render_verdict


class ArgusState(TypedDict):
    txn_id: str
    record: pd.Series
    run_red_team: bool
    graph_features: dict
    score_result: dict
    robustness: Optional[dict]
    verdict_result: dict


def graph_builder_node(state: ArgusState) -> dict:
    return {"graph_features": get_graph_features(state["txn_id"])}


def pattern_analyst_node(state: ArgusState) -> dict:
    return {"score_result": score_transaction(state["record"])}


def red_team_node(state: ArgusState) -> dict:
    return {"robustness": evaluate_robustness(state["record"])}


def verdict_node(state: ArgusState) -> dict:
    return {"verdict_result": render_verdict(state["record"], txn_id=state["txn_id"])}


def _route_after_analyst(state: ArgusState) -> str:
    return "red_team" if state.get("run_red_team") else "verdict"


def build_pipeline():
    graph = StateGraph(ArgusState)
    graph.add_node("graph_builder", graph_builder_node)
    graph.add_node("pattern_analyst", pattern_analyst_node)
    graph.add_node("red_team", red_team_node)
    graph.add_node("verdict", verdict_node)

    graph.set_entry_point("graph_builder")
    graph.add_edge("graph_builder", "pattern_analyst")
    graph.add_conditional_edges(
        "pattern_analyst", _route_after_analyst, {"red_team": "red_team", "verdict": "verdict"}
    )
    graph.add_edge("red_team", "verdict")
    graph.add_edge("verdict", END)
    return graph.compile()


_pipeline = None


def investigate(txn_id, record: pd.Series, run_red_team: bool = False) -> dict:
    """Runs one transaction through the full Argus pipeline. Returns the
    final state, including graph_features, score_result, robustness (if
    requested) and verdict_result."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline.invoke({"txn_id": str(txn_id), "record": record, "run_red_team": run_red_team})
