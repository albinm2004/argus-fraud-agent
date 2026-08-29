"""Pattern Analyst Agent — scores each transaction for fraud risk.

Baseline (live): XGBoost trained on IEEE-CIS + graph-proxy features
(models/pattern_analyst.joblib, produced by scripts/train_baseline.py).
Held-out results: docs/results.md.

Upgrade path (Day 3, not yet built): swap in a small GNN (PyTorch
Geometric) trained directly on the Neo4j entity graph once the Graph
Builder is live, instead of the frequency-count graph-proxy features.
"""
from pathlib import Path

import joblib

_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pattern_analyst.joblib"
_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        if not _MODEL_PATH.exists():
            raise FileNotFoundError(
                f"No trained model at {_MODEL_PATH}. Run scripts/train_baseline.py first."
            )
        _bundle = joblib.load(_MODEL_PATH)
    return _bundle


def score_transaction(feature_row) -> dict:
    """feature_row: a pandas Series (or 1-row DataFrame) already engineered
    to match the training feature set (see agents.features.build_dataset).

    Returns {"score": float, "verdict_flag": bool, "threshold": float}.
    """
    bundle = _load()
    model, feature_cols, threshold = bundle["model"], bundle["feature_cols"], bundle["threshold"]
    x = feature_row[feature_cols].values.reshape(1, -1)
    score = float(model.predict_proba(x)[:, 1][0])
    return {"score": score, "verdict_flag": score >= threshold, "threshold": float(threshold)}
