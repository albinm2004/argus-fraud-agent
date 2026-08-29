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

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_HARDENED_PATH = _MODELS_DIR / "pattern_analyst_hardened.joblib"
_BASELINE_PATH = _MODELS_DIR / "pattern_analyst.joblib"
_bundle = None
_active_path = None


def _load():
    global _bundle, _active_path
    if _bundle is None:
        _active_path = _HARDENED_PATH if _HARDENED_PATH.exists() else _BASELINE_PATH
        if not _active_path.exists():
            raise FileNotFoundError(
                f"No trained model in {_MODELS_DIR}. Run scripts/train_baseline.py first "
                "(and scripts/adversarial_harden.py for the hardened version)."
            )
        _bundle = joblib.load(_active_path)
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
