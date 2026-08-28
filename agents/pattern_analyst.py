"""Pattern Analyst Agent — scores each transaction for fraud risk.

TODO (Day 2-3):
- Baseline: train XGBoost on IEEE-CIS/PaySim + graph features from
  graph_builder.get_graph_features(). Report precision/recall on a
  held-out split.
- Upgrade (Day 3, if baseline is solid): swap in a small GNN
  (PyTorch Geometric) trained directly on the entity graph.
"""


def score_transaction(record: dict, graph_features: dict) -> float:
    raise NotImplementedError
