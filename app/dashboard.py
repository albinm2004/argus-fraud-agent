"""Argus — Streamlit demo surface.

Shows a live-looking feed of held-out transactions with their verdicts,
and the full evidence chain (SHAP attribution + graph signal) behind any
one of them. This is what the 5-minute pitch video points the camera at.

Run: streamlit run app/dashboard.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.features import build_dataset
from agents.pattern_analyst import score_transaction
from agents.verdict import render_verdict
from agents.graph_builder import get_graph_features

st.set_page_config(page_title="Argus — Fraud Investigation", layout="wide")

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@st.cache_data(show_spinner="Loading held-out transactions...")
def load_sample(n=300, seed=42):
    df, feature_cols, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]
    # Oversample fraud a bit vs a pure random sample so the demo has
    # enough positive cases to click through, noted plainly rather than
    # presented as a representative sample.
    fraud = test_df[test_df["isFraud"] == 1].sample(min(n // 3, (test_df["isFraud"] == 1).sum()), random_state=seed)
    legit = test_df[test_df["isFraud"] == 0].sample(n - len(fraud), random_state=seed)
    sample = pd.concat([fraud, legit]).sample(frac=1, random_state=seed).reset_index(drop=True)
    return sample, feature_cols


@st.cache_data
def load_headline_metrics():
    path = MODELS_DIR / "hardening_metrics.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


st.title("Argus")
st.caption("Fraud investigation agent — Razorpay AI Buildathon, Track 2 (AI Risk Manager)")

metrics = load_headline_metrics()
if metrics:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recall (held-out)", f"{metrics['hardened']['recall']*100:.1f}%",
              f"{(metrics['hardened']['recall']-metrics['baseline']['recall'])*100:+.1f}pt vs baseline")
    c2.metric("Precision (held-out)", f"{metrics['hardened']['precision']*100:.1f}%")
    c3.metric("ROC-AUC", f"{metrics['hardened']['roc_auc']:.3f}")
    c4.metric("Adversarial evasion rate", f"{metrics['hardened']['evasion_success_rate']*100:.0f}%",
              f"{(metrics['baseline']['evasion_success_rate']-metrics['hardened']['evasion_success_rate'])*100:.1f}pt improvement",
              delta_color="normal")
    st.caption("Held-out metrics: docs/results.md · Adversarial hardening: docs/hardening_results.md "
               "(evasion rate scoped to the tested perturbation family, not a general robustness claim)")
else:
    st.info("Run scripts/train_baseline.py and scripts/adversarial_harden.py to populate headline metrics.")

st.divider()

sample, feature_cols = load_sample()

left, right = st.columns([1, 1.4])

with left:
    st.subheader("Transaction feed (held-out, sampled)")
    verdict_filter = st.radio("Filter", ["all", "flag/block", "allow"], horizontal=True)

    rows_display = []
    for _, row in sample.iterrows():
        s = score_transaction(row)
        rows_display.append({
            "TransactionID": int(row["TransactionID"]),
            "Amount": round(row["TransactionAmt"], 2),
            "Score": round(s["score"], 3),
            "Verdict": "flag/block" if s["verdict_flag"] else "allow",
            "Actual": "fraud" if row["isFraud"] == 1 else "legit",
        })
    feed_df = pd.DataFrame(rows_display).sort_values("Score", ascending=False)
    if verdict_filter != "all":
        feed_df = feed_df[feed_df["Verdict"] == verdict_filter]

    st.dataframe(feed_df, use_container_width=True, height=420, hide_index=True)
    selected_id = st.selectbox("Inspect a transaction", feed_df["TransactionID"].tolist())

with right:
    st.subheader("Evidence chain")
    if selected_id is not None:
        row = sample[sample["TransactionID"] == selected_id].iloc[0]
        result = render_verdict(row, txn_id=str(selected_id))

        verdict_color = {"block": "red", "flag": "orange", "allow": "green"}[result["verdict"]]
        st.markdown(f"**Verdict: :{verdict_color}[{result['verdict'].upper()}]**  "
                    f"(score {result['score']:.3f}, threshold {result['threshold']:.3f})")
        actual = "FRAUD" if row["isFraud"] == 1 else "legit"
        st.caption(f"Ground truth: {actual}")

        st.markdown("**Why:**")
        for e in result["evidence"]:
            st.markdown(f"- {e}")

        st.markdown("**Graph signal:**")
        gf = get_graph_features(int(selected_id))
        if gf.get("found"):
            st.json(gf)
        else:
            st.caption("Transaction not found in the loaded graph.")
    else:
        st.caption("Select a transaction from the feed.")

st.divider()
st.caption("Argus — built for the Razorpay AI Buildathon. Known limitations tracked honestly in README.md.")
