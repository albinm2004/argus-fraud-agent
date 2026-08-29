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
- [ ] Graph Builder wired to a live Neo4j instance (currently: frequency-count
      graph-proxy features, not a live graph — see `docs/eda_findings.md`)
- [ ] Watcher agent wired to real Razorpay test-mode webhooks
- [ ] Verdict + Audit evidence chain (SHAP-backed)
- [ ] Streamlit demo surface

## Known limitations

- Only ~24% of transactions carry an identity/device record (`docs/eda_findings.md`) —
  device-based signal is real but partial, not universal.
- The Graph Builder is not yet live against Neo4j; the baseline currently
  uses frequency-count proxies (`card1`/`addr1`/`card1+addr1`) for the same
  signal, standing in until the real graph is wired up.
- ~32% of correctly-caught fraud evaded the *baseline* model under realistic
  adversarial perturbation (`docs/adversarial_results.md`); the hardened
  model (now default) closed that to 0% on the same attack family, but
  that is not a general robustness guarantee — see `docs/hardening_results.md`.
- The operating threshold was chosen on the held-out set itself for
  reporting; a production deployment would pick it on a separate
  validation split.
