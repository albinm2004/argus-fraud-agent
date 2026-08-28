# Argus — Architecture

## Pipeline

```
Watcher --> Graph Builder --> Pattern Analyst --> Adversarial Red-Team --> Verdict + Audit
                                     ^                      |
                                     +----------------------+
                                     (evasion found -> retrain/re-score)
```

## Agents

### Watcher
Subscribes to Razorpay test-mode Orders and Payment Links webhooks.
Normalizes each event into a transaction record: amount, card fingerprint,
device ID, IP, user ID, merchant ID, timestamp.

### Graph Builder
Writes each transaction's entities into Neo4j as nodes, with edges for
shared cards, devices, and IPs across different users/transactions. This is
what surfaces fraud-ring structure a row-by-row classifier would miss.

### Pattern Analyst
Scores each transaction for fraud risk.
- **Baseline**: gradient boosting (XGBoost) over graph-derived features
  (centrality, community membership, shared-entity counts).
- **Upgrade**: a small Graph Neural Network (PyTorch Geometric) that learns
  fraud-ring structure directly from the entity graph instead of relying on
  hand-engineered features.

### Adversarial Red-Team
Runs evasion attacks against the Analyst's own model — perturbing feature
patterns to find what a motivated fraudster could slip past — and reports a
robustness delta (accuracy/recall before vs. after adversarial perturbation).

### Verdict + Audit
Renders block / flag / allow. Writes a plain-language evidence chain per
decision:
- **Baseline**: describes the graph features that drove the score.
- **Upgrade**: backs the evidence chain with real SHAP feature attribution.

Logs every verdict, its evidence, and the ground truth (where known) for the
held-out precision/recall report.

## Data plan

Training/eval data (IEEE-CIS / PaySim) is kept separate from the live
Razorpay test-mode integration deliberately — the held-out metric needs
real fraud labels that Razorpay's test mode doesn't provide, and the API
integration needs to be demonstrated against the actual required tech
stack regardless of where the training labels came from.

## Metrics tracked

- Precision / recall on a held-out test split
- Adversarial robustness delta (pre/post red-team)
- Latency per verdict
- Known failure modes (maintained honestly, not hidden)
