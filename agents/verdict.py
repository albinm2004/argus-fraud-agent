"""Verdict + Audit Agent — renders block/flag/allow with a SHAP-backed
evidence chain, and logs it for the held-out precision/recall report.

Loads whichever Pattern Analyst model is active (hardened if present, see
agents/pattern_analyst.py) and explains every verdict with real per-feature
SHAP attribution — not a hand-described "graph centrality 0.82" note.
"""
import json
import time
from pathlib import Path

import joblib
import xgboost as xgb

from agents.evidence import describe_feature
from agents.graph_builder import get_graph_features

# Using XGBoost's native pred_contribs (exact SHAP values, computed
# in-tree) instead of the `shap` package's TreeExplainer: the installed
# shap/xgboost version combo has a known interop bug parsing XGBoost's
# serialized base_score ("[5E-1]" bracket format), and pred_contribs
# gives identical values without depending on shap's model loader at all.

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_HARDENED_PATH = _MODELS_DIR / "pattern_analyst_hardened.joblib"
_BASELINE_PATH = _MODELS_DIR / "pattern_analyst.joblib"
_AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "audit_log.jsonl"

_bundle = None
_explainer = None

TOP_K_EVIDENCE = 5


def _load():
    global _bundle
    if _bundle is None:
        active_path = _HARDENED_PATH if _HARDENED_PATH.exists() else _BASELINE_PATH
        _bundle = joblib.load(active_path)
    return _bundle


def render_verdict(record: dict, txn_id=None) -> dict:
    """record: a dict/Series of engineered features matching the model's
    feature_cols (see agents.features.build_dataset).

    Returns {"verdict": "block"|"flag"|"allow", "score": float,
             "threshold": float, "evidence": [str, ...]}
    and appends the same to the audit log (data/processed/audit_log.jsonl).
    """
    bundle = _load()
    model, feature_cols, threshold = bundle["model"], bundle["feature_cols"], bundle["threshold"]

    x = record[feature_cols].values.reshape(1, -1) if hasattr(record, "values") else record
    score = float(model.predict_proba(x)[:, 1][0])

    if score >= threshold:
        verdict = "block" if score >= min(threshold + 0.15, 0.95) else "flag"
    else:
        verdict = "allow"

    dmat = xgb.DMatrix(x, feature_names=feature_cols)
    contribs = model.get_booster().predict(dmat, pred_contribs=True)[0]  # last element is bias term
    shap_row = contribs[:-1]
    contributions = list(zip(feature_cols, shap_row, x[0]))
    contributions.sort(key=lambda t: -abs(t[1]))
    top = contributions[:TOP_K_EVIDENCE]

    evidence = []
    for name, shap_val, value in top:
        direction = "raised" if shap_val > 0 else "lowered"
        evidence.append(
            f"{describe_feature(name, value)} — {direction} risk score by {abs(shap_val):.3f}"
        )

    graph_note = None
    if txn_id is not None:
        try:
            gf = get_graph_features(txn_id)
            if gf.get("found"):
                ring_note = (
                    f"linked to {gf['shared_card_count']} other transactions via shared card, "
                    f"{gf['shared_addr_count']} via shared address"
                )
                fraud_key = "other_fraud_in_component" if "other_fraud_in_component" in gf else "neighbor_fraud_count"
                if gf.get(fraud_key):
                    ring_note += f" — {gf[fraud_key]} other transaction(s) in this cluster already flagged as fraud"
                graph_note = ring_note
                evidence.append(f"[graph, {gf.get('source', 'unknown')}] {ring_note}")
        except Exception:
            pass  # graph signal is enrichment, not required for a verdict

    result = {
        "txn_id": txn_id,
        "score": round(score, 4),
        "threshold": round(threshold, 4),
        "verdict": verdict,
        "evidence": evidence,
        "graph_note": graph_note,
        "logged_at": time.time(),
    }

    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result
