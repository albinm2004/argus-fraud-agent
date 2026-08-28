"""Streamlit demo surface — shows a flagged transaction and its evidence chain.

TODO (Day 5):
- Table/feed of recent transactions with their verdicts.
- Click a transaction -> show its evidence chain (graph neighbors + SHAP
  attribution) and the graph structure around it.
- This is what the 5-minute pitch video points the camera at.
"""
import streamlit as st

st.set_page_config(page_title="Argus — Fraud Investigation", layout="wide")
st.title("Argus")
st.caption("Fraud investigation agent — Razorpay AI Buildathon, Track 2")
st.info("Dashboard scaffolded. Wiring up to the Verdict Agent's audit log is Day 5 work.")
