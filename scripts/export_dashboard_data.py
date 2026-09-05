"""Argus -- exports precomputed pipeline output for the React showcase frontend
(frontend/). See claude/frontend-react-plan.md (project doc) for why this is a
precomputed export rather than a live API: it removes an entire backend build
+ integration-test surface at a point in the project where that risk isn't
worth taking, while keeping every number genuinely real -- this runs the SAME
render_verdict() / get_graph_features() / evaluate_robustness() code the
Streamlit dashboard and webhook receiver use, just once, ahead of time,
instead of on every page load.

Uses the SAME sample (n=300, seed=42) as app/dashboard.py's load_sample(), so
the two frontends show the same transactions -- not a coincidence, a deliberate
parity choice so neither one can quietly show a rosier picture than the other.

Red-team (adversarial robustness) checks are expensive (40 predict_proba
calls each), so they're computed for a representative subset (the N_RED_TEAM
transactions closest to the decision threshold -- the genuinely interesting,
borderline cases) rather than for all 300.

Run: PYTHONPATH=. python scripts/export_dashboard_data.py
Writes: frontend/public/data/dashboard.json

Re-run this from your OWN terminal (not the sandboxed bridge shell) after
Neo4j has real data loaded (scripts/load_graph_to_neo4j.py) to pick up live
"source": "neo4j" graph signals instead of the local networkx fallback.
"""
import json
import time
from pathlib import Path

import pandas as pd

from agents.features import build_dataset
from agents.graph_builder import get_graph_features
from agents.pattern_analyst import score_transaction
from agents.red_team import evaluate_robustness
from agents.verdict import render_verdict

N_SAMPLE = 300
SEED = 42
N_RED_TEAM = 15

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
OUT_PATH = REPO_ROOT / "frontend" / "public" / "data" / "dashboard.json"


def load_sample(n=N_SAMPLE, seed=SEED):
    df, feature_cols, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]
    fraud = test_df[test_df["isFraud"] == 1].sample(
        min(n // 3, (test_df["isFraud"] == 1).sum()), random_state=seed)
    legit = test_df[test_df["isFraud"] == 0].sample(n - len(fraud), random_state=seed)
    sample = pd.concat([fraud, legit]).sample(frac=1, random_state=seed).reset_index(drop=True)
    return sample, feature_cols


def parse_evidence_line(text: str):
    """Mirrors app/dashboard.py's evidence_bar_row() parsing so both frontends
    render the exact same bars from the exact same text -- one source of truth."""
    raised = "raised risk" in text
    lowered = "lowered risk" in text
    if not (raised or lowered):
        return {"text": text, "direction": None, "magnitude": None}
    try:
        magnitude = float(text.rsplit("by", 1)[1].strip())
    except (ValueError, IndexError):
        magnitude = None
    return {"text": text, "direction": "raised" if raised else "lowered", "magnitude": magnitude}


def main():
    t0 = time.time()
    print("Loading held-out sample (same n=300, seed=42 as the Streamlit dashboard)...")
    sample, feature_cols = load_sample()

    metrics_path = MODELS_DIR / "hardening_metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else None

    print(f"Scoring {len(sample)} transactions (full evidence chain + graph signal each)...")
    transactions = []
    for i, row in sample.iterrows():
        txn_id = int(row["TransactionID"])
        quick = score_transaction(row)
        result = render_verdict(row, txn_id=str(txn_id))
        gf = get_graph_features(txn_id)
        transactions.append({
            "id": txn_id,
            "amount": round(float(row["TransactionAmt"]), 2),
            "score": round(result["score"], 4),
            "threshold": round(result["threshold"], 4),
            "verdict": result["verdict"],
            "verdict_bucket": "flag/block" if quick["verdict_flag"] else "allow",
            "actual": "fraud" if row["isFraud"] == 1 else "legit",
            "evidence": [parse_evidence_line(e) for e in result["evidence"]],
            "graph": gf,
            "red_team": None,  # filled in below for the pinned subset
        })
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(sample)} ({time.time() - t0:.0f}s elapsed)")

    print(f"Running red-team robustness checks on the {N_RED_TEAM} most borderline transactions...")
    by_distance = sorted(range(len(transactions)),
                          key=lambda idx: abs(transactions[idx]["score"] - transactions[idx]["threshold"]))
    red_team_idx = by_distance[:N_RED_TEAM]
    id_to_row = {int(r["TransactionID"]): r for _, r in sample.iterrows()}
    for idx in red_team_idx:
        txn = transactions[idx]
        row = id_to_row[txn["id"]]
        rt = evaluate_robustness(row[feature_cols])
        txn["red_team"] = {
            "pre": round(rt["pre_attack_score"], 4),
            "post": round(rt["post_attack_score"], 4),
            "evaded": rt["evaded"],
        }

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_sample": len(transactions),
        "n_red_team": N_RED_TEAM,
        "metrics": metrics,
        "transactions": transactions,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    neo4j_count = sum(1 for t in transactions if t["graph"].get("source") == "neo4j")
    print(f"\nDone in {time.time() - t0:.0f}s. Wrote {OUT_PATH}")
    print(f"Graph signal source: {neo4j_count}/{len(transactions)} from live neo4j, "
          f"{len(transactions) - neo4j_count} from local networkx fallback.")

    if neo4j_count:
        # get_graph_features() above opened a module-level Neo4j driver that stays
        # alive for a long-running process (webhook receiver, dashboard) -- but this
        # is a short-lived script, so close it explicitly before exiting. Otherwise
        # Python tears the socket down mid-flight on interpreter exit instead of via
        # the driver's normal GOODBYE handshake, which prints a scary-looking (but
        # harmless) "Failed to write data to connection ..." warning. See
        # agents/graph_builder_neo4j.py's close_driver() docstring.
        from agents.graph_builder_neo4j import close_driver
        close_driver()


if __name__ == "__main__":
    main()
