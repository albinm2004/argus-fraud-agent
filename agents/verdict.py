"""Verdict + Audit Agent — renders block/flag/allow with an evidence chain.

TODO (Day 3, Day 5 for SHAP upgrade):
- Threshold the Pattern Analyst's score into block / flag / allow.
- Baseline evidence chain: describe the graph features that drove the score.
- Upgrade: back the evidence chain with real SHAP attribution per feature.
- Log every verdict + evidence + (ground truth, where known) for the
  held-out precision/recall report.
"""


def render_verdict(record: dict, score: float, graph_features: dict) -> dict:
    """Returns {"verdict": "block"|"flag"|"allow", "evidence": [...]}"""
    raise NotImplementedError
