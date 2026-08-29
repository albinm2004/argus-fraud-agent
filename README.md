# Argus — Fraud Investigation Agent

Built for the **Razorpay AI Buildathon**, Track 2 (AI Risk Manager).

Argus is a multi-agent fraud detector that treats every transaction like a case
file: it builds an entity graph around the transaction, scores it, red-teams
its own scoring model for evasion weaknesses, and produces a plain-language
evidence chain for every verdict — not a bare risk number.

## Why this exists

Track 2 asks for *"a working detector, verifier or auto-responder for one
class of loss, with measured precision and recall on a held-out test set."*
Argus answers that directly, plus two things most fraud demos skip:

- **An audit trail per decision** — every block/flag/allow comes with the
  evidence behind it (linked entities, feature attribution), not just a score.
- **An adversarial robustness result** — the model is stress-tested against
  its own evasion attempts before it's trusted, not just accuracy-reported.

## Architecture

Five agents, one audit trail:

1. **Watcher** — ingests Razorpay test-mode Orders/Payment Links events
2. **Graph Builder** — writes transaction entities (card, device, IP, user,
   merchant) into Neo4j, linking shared attributes across transactions
3. **Pattern Analyst** — scores each transaction; baseline is gradient
   boosting over graph features, upgrade path is a small GNN
   (PyTorch Geometric) trained directly on the entity graph
4. **Adversarial Red-Team** — attacks the Analyst's own model to find
   evasion patterns, reports a robustness delta
5. **Verdict + Audit** — renders block/flag/allow with a plain-language
   evidence chain (SHAP-backed where available) and logs it for the
   held-out precision/recall report

Full diagram and rationale: [`docs/architecture.md`](docs/architecture.md).

## Data plan

- **Training / evaluation**: IEEE-CIS Fraud Detection or PaySim (public,
  labeled) — used to produce a real, honest precision/recall number on a
  held-out split. See `scripts/download_dataset.py`.
- **Live pipeline demo**: Razorpay test-mode API — proves the agent
  pipeline works against the real required tech stack, independent of
  where the training labels came from.

## Testing

`PYTHONPATH=. python -m pytest tests/ -v` — 11 tests covering webhook
signature verification, event normalization, the TransactionID dtype
regression (see Known limitations), and an end-to-end pipeline smoke test.

## Setup

1. `cp .env.example .env` and fill in Razorpay test keys, Neo4j AuraDB
   credentials, and (optionally) your Kaggle API token.
2. `pip install -r requirements.txt`
3. Download IEEE-CIS Fraud Detection into `data/raw/ieee-fraud-detection/`
   (join the competition at kaggle.com/c/ieee-fraud-detection first, it's
   a one-click accept, then `kaggle competitions download -c ieee-fraud-detection`).
4. `PYTHONPATH=. python scripts/train_baseline.py` — trains the baseline
   Pattern Analyst, writes `models/pattern_analyst.joblib` and `docs/results.md`.
5. `PYTHONPATH=. python scripts/red_team_attack.py` — runs the adversarial
   evasion sweep, writes `docs/adversarial_results.md`.
6. Install PyTorch + PyTorch Geometric separately (platform-specific —
   see pytorch.org/get-started/locally and the PyTorch Geometric install
   docs) only when the GNN upgrade is in scope.
7. `PYTHONPATH=. python scripts/demo_replay.py` — the quickest way to see
   the whole system work: signs a real Razorpay-shaped webhook, verifies
   it, runs it through the live LangGraph pipeline against a few held-out
   transactions, and prints the verdict + evidence chain for each.

## Status (updated as the build progresses)

- [x] EDA over the full dataset — see `docs/eda_findings.md`
- [x] Baseline Pattern Analyst trained and held out honestly — see `docs/results.md`
      (precision 0.50, recall 0.47, ROC-AUC 0.91 on a time-based split)
- [x] Adversarial red-team pass — see `docs/adversarial_results.md`
      (~32% of caught fraud evaded under realistic perturbation on the baseline model)
- [x] Adversarial-training hardening pass — see `docs/hardening_results.md`
      (evasion dropped from 32.8% to 0.0% on a fixed held-out sample, for a
      ~0.3pt recall cost; scoped to this attack family, not general robustness —
      see that doc's known limitations. Hardened model is now the default
      `agents/pattern_analyst.py` loads.)
- [x] Graph Builder — real graph (networkx locally, tries live Neo4j AuraDB
      first and falls back automatically). Excludes ~60 hub addresses AND
      ~430 hub cards (found via end-to-end pipeline testing, not just unit
      tests — see `docs/architecture.md`) that otherwise collapse the graph
      into one giant component. Ring-like components found: 8,772 (3-100
      txns each), zero components over 1,000 nodes.
- [x] `scripts/demo_replay.py` — end-to-end demo: signs and verifies a real
      Razorpay-shaped webhook (Watcher), runs it through the actual
      LangGraph pipeline against held-out transactions, prints verdict +
      evidence + graph signal. This is the script used for the pitch demo.
- [x] Watcher agent — real Razorpay webhook signature verification (HMAC-SHA256)
      and event normalization against the documented payload shape. Honest
      limitation: Razorpay webhooks don't carry device/IP directly; `device_id`
      is only populated if the checkout flow passes one through `notes`.
- [x] Verdict + Audit evidence chain — real per-feature attribution via
      XGBoost's native SHAP (`pred_contribs`), not a hand-described note.
      Logs every verdict to `data/processed/audit_log.jsonl`.
- [x] Streamlit demo surface (`app/dashboard.py`) — transaction feed +
      full evidence chain per transaction, boot-tested and working.
- [x] Razorpay connectivity verified live — `scripts/smoke_test_integrations.py`
      run from a real terminal with internet access confirms auth works
      against the test-mode key.
- [ ] Live Neo4j connectivity verified — blocked so far by an environment
      bug, not a code bug: installing from `requirements.txt` on Windows/
      Python 3.13 could downgrade numpy to an exact version that hits a
      known `OverflowError` in numpy's longdouble handling the moment
      `neo4j` imports numpy, before a connection is even attempted. Pin
      loosened in `requirements.txt` (`numpy>=1.26,<2.3`) to avoid forcing
      that exact version; rerun `scripts/smoke_test_integrations.py` after
      `pip install --upgrade -r requirements.txt` to confirm.

## Pitch video

`docs/pitch_script.md` -- a 5-minute script mapped to what's actually in this repo (real numbers, the demo command, the two bugs caught during end-to-end testing). Draft, adjust to your own voice, then record.

## Known limitations

- Only ~24% of transactions carry an identity/device record (`docs/eda_findings.md`) —
  device-based signal is real but partial, not universal.
- The Graph Builder's live Neo4j path (`agents/graph_builder_neo4j.py`) is
  written and unit-tested for the key-normalization bug, but not yet
  confirmed against a live AuraDB connection from a real network (see
  Status above) — it automatically falls back to the local networkx graph
  (built from the same frequency-count signal) if Neo4j isn't reachable.
- ~32% of correctly-caught fraud evaded the *baseline* model under realistic
  adversarial perturbation (`docs/adversarial_results.md`); the hardened
  model (now default) closed that to 0% on the same attack family, but
  that is not a general robustness guarantee — see `docs/hardening_results.md`.
- The operating threshold was chosen on the held-out set itself for
  reporting; a production deployment would pick it on a separate
  validation split.
- Found and fixed during pipeline wiring: pulling a single row out of a
  mixed-dtype DataFrame silently upcasts `TransactionID` to float
  (`3459499.0`), which broke every graph lookup until caught by testing
  the pipeline end-to-end, not just each agent in isolation. Regression
  test added (`tests/test_graph_builder.py`) so it can't come back quietly.
- Found and fixed the same way (`scripts/demo_replay.py`, real webhook
  through the real pipeline): the local graph excluded hub *addresses*
  but not hub *cards*, so a popular card1 value collapsed 46% of the
  dataset into one giant "ring" -- a demoed transaction's evidence cited
  13,169 fraud neighbors, which is population noise, not a ring. Fixed by
  capping card1 the same way (`CARD_HUB_CAP` in `agents/graph_builder.py`);
  the local graph now has zero components over 1,000 nodes.
- The Watcher agent's real-time signature verification and event
  normalization are unit-tested and correct, but the gap between a raw
  webhook payload and the full 60-feature vector the model expects (C1-C14
  velocity signals, graph-proxy frequencies, etc.) is NOT solved -- that
  needs a live feature store built from transaction history, which is out
  of scope for this build. Documented in `agents/pipeline.py` rather than
  hidden behind a fake mapping.
