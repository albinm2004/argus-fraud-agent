"""Adversarial Red-Team Agent — attacks the Analyst's own model.

Live implementation: scripts/red_team_attack.py runs the full black-box
evasion sweep and writes docs/adversarial_results.md. This module exposes
the same single-transaction perturbation search so the Verdict Agent can
optionally report a per-transaction robustness note, not just the
aggregate offline number.

Baseline result (docs/adversarial_results.md): ~32% of correctly-flagged
fraud evaded detection under realistic amount/velocity perturbation.

Hardening result (docs/hardening_results.md): after adversarial-training
hardening on this exact perturbation family, evasion dropped to 0% on a
fixed held-out sample, at a roughly 0.3pt recall cost. This module now
loads the hardened model by default when it exists. The 0% figure is
scoped to this attack family (see hardening doc's known limitations) --
not a claim of general robustness.
"""
from pathlib import Path

import joblib
import numpy as np

from agents.features import PERTURBABLE_COLS
from agents.perturbation import best_evasion

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_HARDENED_PATH = _MODELS_DIR / "pattern_analyst_hardened.joblib"
_BASELINE_PATH = _MODELS_DIR / "pattern_analyst.joblib"
_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        active_path = _HARDENED_PATH if _HARDENED_PATH.exists() else _BASELINE_PATH
        _bundle = joblib.load(active_path)
    return _bundle


def evaluate_robustness(feature_row, n_candidates: int = 40, jitter: float = 0.35, seed: int = 42) -> dict:
    """Runs the same perturbation search as scripts/red_team_attack.py
    against a single transaction's feature row. Returns the original score,
    the best evasion score found, and whether it flips the verdict.

    Was previously a hand-copied re-implementation of the jitter search
    living right here in this function -- despite this module's own
    docstring and agents/perturbation.py's docstring both claiming the
    live agent "searches the same way" as the offline attack/hardening
    scripts. That claim was only true by coincidence of copy-paste, not
    by actually sharing code: a future edit to the jitter logic in one
    place could silently drift out of sync with the other and make the
    live per-transaction "robustness note" stop matching the methodology
    documented in docs/adversarial_results.md. Fixed by calling the
    actually-shared agents.perturbation.best_evasion() here -- verified
    to produce identical pre/post scores on real held-out fraud rows
    before and after this change (same algorithm, just no longer
    duplicated)."""
    bundle = _load()
    model, feature_cols, threshold = bundle["model"], bundle["feature_cols"], bundle["threshold"]
    rng = np.random.default_rng(seed)

    row = feature_row[feature_cols].values.astype(float)
    pre_score = float(model.predict_proba(row.reshape(1, -1))[:, 1][0])

    _, post_score = best_evasion(model, row, feature_cols, PERTURBABLE_COLS, n_candidates, jitter, rng)

    return {
        "pre_attack_score": pre_score,
        "post_attack_score": float(post_score),
        "evaded": bool(pre_score >= threshold and post_score < threshold),
        "threshold": float(threshold),
    }
