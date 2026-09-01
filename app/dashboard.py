"""Argus -- Streamlit demo surface.

Shows a live-looking feed of held-out transactions with their verdicts,
and the full evidence chain (SHAP attribution + graph signal) behind any
one of them. This is what the 5-minute pitch video points the camera at.

Visual design follows a status/diverging color convention rather than
default Streamlit styling: verdict badges use a fixed status palette
(never color alone -- every badge and bar carries a text label too), and
per-feature evidence bars use a diverging blue<->red scale (blue =
lowered risk, red = raised risk) anchored at a center zero-line, which is
the correct chart form for a signed contribution value, not an
arbitrary-origin bar chart.

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

st.set_page_config(page_title="Argus — Fraud Investigation", page_icon="🛡️", layout="wide")

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# -- Palette (status + diverging jobs only -- see docs/architecture.md for
# the pipeline diagram this dashboard visualizes one slice of) --------------
STATUS = {
    "block": {"hex": "#d03b3b", "label": "BLOCK", "bg": "#fbe9e9"},
    "flag": {"hex": "#fab219", "label": "FLAG", "bg": "#fef6e6"},
    "allow": {"hex": "#0ca30c", "label": "ALLOW", "bg": "#e9f7e9"},
}
DIVERGE_UP = "#d03b3b"     # raised risk
DIVERGE_DOWN = "#2a78d6"   # lowered risk
INK_MUTED = "#898781"
INK_SECONDARY = "#52514e"

CUSTOM_CSS = f"""
<style>
.argus-hero {{
    display: flex; align-items: center; gap: 14px;
    padding: 4px 0 18px 0; border-bottom: 1px solid #e1e0d9; margin-bottom: 18px;
}}
.argus-hero .shield {{ font-size: 2.2rem; line-height: 1; }}
.argus-hero .title {{ font-size: 1.6rem; font-weight: 700; margin: 0; }}
.argus-hero .tagline {{ color: {INK_SECONDARY}; font-size: 0.92rem; margin: 0; }}

.verdict-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 12px; border-radius: 999px; font-weight: 700;
    font-size: 0.85rem; letter-spacing: 0.02em;
}}
.verdict-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}

.score-scale {{ position: relative; height: 34px; margin: 10px 0 4px 0; }}
.score-scale .track {{
    position: absolute; top: 14px; left: 0; right: 0; height: 6px;
    border-radius: 3px; background: #e1e0d9;
}}
.score-scale .fill {{
    position: absolute; top: 14px; left: 0; height: 6px; border-radius: 3px;
}}
.score-scale .threshold-tick {{
    position: absolute; top: 6px; width: 2px; height: 22px; background: {INK_SECONDARY};
}}
.score-scale .marker {{
    position: absolute; top: 8px; width: 14px; height: 14px; border-radius: 50%;
    border: 2px solid white; box-shadow: 0 0 0 1px rgba(11,11,11,0.15); transform: translateX(-50%);
}}
.score-scale-labels {{ display: flex; justify-content: space-between; font-size: 0.72rem; color: {INK_MUTED}; }}

.evidence-row {{ margin: 10px 0; }}
.evidence-text {{ font-size: 0.88rem; margin-bottom: 3px; }}
.evidence-bar-track {{
    position: relative; height: 10px; background: #f2f1ed; border-radius: 3px; overflow: visible;
}}
.evidence-bar-center {{ position: absolute; left: 50%; top: -2px; width: 1px; height: 14px; background: #c3c2b7; }}
.evidence-bar-fill {{ position: absolute; top: 0; height: 10px; border-radius: 3px; }}

.chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 6px 0 2px 0; }}
.chip {{
    background: #f2f1ed; border-radius: 6px; padding: 4px 10px;
    font-size: 0.8rem; color: {INK_SECONDARY};
}}
.chip b {{ color: #0b0b0b; }}

.pipeline-strip {{ display: flex; align-items: center; gap: 4px; margin: 4px 0 14px 0; flex-wrap: wrap; }}
.pipeline-node {{
    font-size: 0.72rem; padding: 3px 9px; border-radius: 5px; background: #f2f1ed;
    color: {INK_MUTED}; border: 1px solid #e1e0d9;
}}
.pipeline-node.active {{ background: #e8f0fe; color: #184f95; border-color: #2a78d6; font-weight: 600; }}
.pipeline-arrow {{ color: {INK_MUTED}; font-size: 0.75rem; }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="argus-hero"><span class="shield">🛡️</span>'
    '<div><p class="title">Argus</p>'
    '<p class="tagline">Multi-agent fraud investigation — Razorpay AI Buildathon, Track 2 (AI Risk Manager)</p>'
    '</div></div>',
    unsafe_allow_html=True,
)


def verdict_badge(verdict: str) -> str:
    s = STATUS.get(verdict, STATUS["allow"])
    return (f'<span class="verdict-badge" style="background:{s["bg"]}; color:{s["hex"]}">'
            f'<span class="verdict-dot" style="background:{s["hex"]}"></span>{s["label"]}</span>')


def score_scale(score: float, threshold: float, verdict: str) -> str:
    color = STATUS.get(verdict, STATUS["allow"])["hex"]
    score_pct = max(0.0, min(1.0, score)) * 100
    thresh_pct = max(0.0, min(1.0, threshold)) * 100
    return f"""
    <div class="score-scale">
        <div class="track"></div>
        <div class="fill" style="width:{score_pct:.1f}%; background:{color};"></div>
        <div class="threshold-tick" style="left:{thresh_pct:.1f}%;" title="Decision threshold {threshold:.3f}"></div>
        <div class="marker" style="left:{score_pct:.1f}%; background:{color};"></div>
    </div>
    <div class="score-scale-labels"><span>0.0</span><span>score {score:.3f} · threshold {threshold:.3f}</span><span>1.0</span></div>
    """


def evidence_bar_row(text: str) -> str:
    """text looks like '<description> — raised/lowered risk score by <magnitude>'.
    Parses direction + magnitude out to size and color a diverging bar; falls
    back to a plain row (no bar) if the format doesn't match, e.g. the
    graph-signal evidence line, which carries no numeric magnitude."""
    raised = "raised risk" in text
    lowered = "lowered risk" in text
    if not (raised or lowered):
        return f'<div class="evidence-row"><div class="evidence-text">{text}</div></div>'
    try:
        magnitude = float(text.rsplit("by", 1)[1].strip())
    except (ValueError, IndexError):
        magnitude = 0.3
    pct = min(48.0, magnitude * 60)  # visual scale, capped so bars stay inside the track
    color = DIVERGE_UP if raised else DIVERGE_DOWN
    left = 50.0 if raised else 50.0 - pct
    width = pct
    return f"""
    <div class="evidence-row">
        <div class="evidence-text">{text}</div>
        <div class="evidence-bar-track">
            <div class="evidence-bar-center"></div>
            <div class="evidence-bar-fill" style="left:{left:.1f}%; width:{width:.1f}%; background:{color};"></div>
        </div>
    </div>
    """


def pipeline_strip(ran_red_team: bool) -> str:
    nodes = ["Watcher", "Graph Builder", "Pattern Analyst"]
    nodes.append("Red-Team" if ran_red_team else "Red-Team (skipped)")
    nodes.append("Verdict")
    active = [True, True, True, ran_red_team, True]
    parts = []
    for i, (name, is_active) in enumerate(zip(nodes, active)):
        cls = "pipeline-node active" if is_active else "pipeline-node"
        parts.append(f'<span class="{cls}">{name}</span>')
        if i < len(nodes) - 1:
            parts.append('<span class="pipeline-arrow">→</span>')
    return f'<div class="pipeline-strip">{"".join(parts)}</div>'


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

    def _row_style(row):
        color = "#fbe9e9" if row["Verdict"] == "flag/block" else "#e9f7e9"
        return [f"background-color: {color}" if col == "Verdict" else "" for col in row.index]

    st.dataframe(feed_df.style.apply(_row_style, axis=1), width="stretch", height=420, hide_index=True)
    selected_id = st.selectbox("Inspect a transaction", feed_df["TransactionID"].tolist())

with right:
    st.subheader("Evidence chain")
    if selected_id is not None:
        row = sample[sample["TransactionID"] == selected_id].iloc[0]
        result = render_verdict(row, txn_id=str(selected_id))

        st.markdown(verdict_badge(result["verdict"]), unsafe_allow_html=True)
        actual = "FRAUD" if row["isFraud"] == 1 else "legit"
        st.caption(f"Ground truth: {actual}  ·  txn {selected_id}")
        st.markdown(score_scale(result["score"], result["threshold"], result["verdict"]), unsafe_allow_html=True)
        st.markdown(pipeline_strip(ran_red_team=False), unsafe_allow_html=True)

        st.markdown("**Why:**")
        for e in result["evidence"]:
            st.markdown(evidence_bar_row(e), unsafe_allow_html=True)
        st.caption("Red bars raised the risk score, blue bars lowered it — bar length is the magnitude of that "
                   "feature's SHAP contribution (XGBoost native `pred_contribs`, not the `shap` package).")

        st.markdown("**Graph signal:**")
        gf = get_graph_features(int(selected_id))
        if gf.get("found"):
            fraud_key = "other_fraud_in_component" if "other_fraud_in_component" in gf else "neighbor_fraud_count"
            chips = [
                f'<span class="chip">Source: <b>{gf.get("source", "unknown")}</b></span>',
                f'<span class="chip">Shared card: <b>{gf.get("shared_card_count", 0)}</b></span>',
                f'<span class="chip">Shared address: <b>{gf.get("shared_addr_count", 0)}</b></span>',
            ]
            if fraud_key in gf:
                chips.append(f'<span class="chip">Fraud nearby: <b>{gf[fraud_key]}</b></span>')
            st.markdown(f'<div class="chip-row">{"".join(chips)}</div>', unsafe_allow_html=True)
        else:
            st.caption("Transaction not found in the loaded graph.")
    else:
        st.caption("Select a transaction from the feed.")

st.divider()
st.caption("Argus — built for the Razorpay AI Buildathon. Known limitations tracked honestly in README.md.")
