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
3. Install PyTorch + PyTorch Geometric separately (platform-specific —
   see https://pytorch.org/get-started/locally/ and
   https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html)
   only if/when the GNN upgrade is in scope.
4. `python scripts/download_dataset.py` to pull the training data.

## Status

Early scaffold — see `docs/architecture.md` for the build plan and
`docs/results.md` (once it exists) for the held-out metrics and the
adversarial robustness delta.

## Known limitations

_(kept honest and updated as the build progresses — judging explicitly
rewards naming these rather than hiding them)_
