"""Adversarial Red-Team Agent — attacks the Analyst's own model.

Live implementation: scripts/red_team_attack.py runs the full black-box
evasion sweep and writes docs/adversarial_results.md. This module exposes
the same single-transaction perturbation search so the Verdict Agent can
optionally report a per-transaction robustness note, not just the
aggregate offline number.

Result so far (see docs/adversarial_results.md): ~32% of correctly-flagged
fraud evades detection under realistic amount/velocity perturbation.
Adversarial-training hardening is the planned next step, not yet built.
"""
from pathlib import Path

import joblib
import numpy as np

from agents.features import PERTURBABLE_COLS

_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pattern_analyst.joblib"
_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(_MODEL_PATH)
    return _bundle


def evaluate_robustness(feature_row, n_candidates: int = 40, jitter: float = 0.35, seed: int = 42) -> dict:
    """Runs the same perturbation search as scripts/red_team_attack.py
    against a single transaction's feature row. Returns the original score,
    the best evasion score found, and whether it flips the verdict."""
    bundle = _load()
    model, feature_cols, threshold = bundle["model"], bundle["feature_cols"], bundle["threshold"]
    rng = np.random.default_rng(seed)

    row = feature_row[feature_cols].values.astype(float)
    pre_score = float(model.predict_proba(row.reshape(1, -1))[:, 1][0])

    perturbable_idx = [feature_cols.index(c) for c in PERTURBABLE_COLS if c in feature_cols]
    batch = np.tile(row, (n_candidates, 1))
    for idx in perturbable_idx:
        base = batch[:, idx]
        factors = rng.uniform(1 - jitter, 1 + jitter, size=n_candidates)
        jittered = base * factors
        jittered = np.where(np.abs(base) < 1e-6, rng.uniform(-1, 1, size=n_candidates), jittered)
        batch[:, idx] = jittered

    probs = model.predict_proba(batch)[:, 1]
    post_score = float(probs.min())

    return {
        "pre_attack_score": pre_score,
        "post_attack_score": post_score,
        "evaded": bool(pre_score >= threshold and post_score < threshold),
        "threshold": float(threshold),
    }
