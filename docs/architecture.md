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

## Orchestration (live)

`agents/pipeline.py` wires the pipeline as an actual LangGraph `StateGraph`,
not just independently-callable functions:

```
Graph Builder --> Pattern Analyst --> [Red-Team, conditional] --> Verdict + Audit
```

`investigate(txn_id, record, run_red_team=False)` runs one transaction
through the full graph and returns every intermediate result (graph
signal, score, optional robustness check, final verdict + evidence
chain). Boot-tested via `tests/test_pipeline.py`.

**Scope boundary, stated plainly**: this operates on an already-engineered
feature row, not a raw Razorpay webhook. The Watcher agent's real job --
HMAC-SHA256 signature verification and payload normalization -- is built
and unit-tested (`tests/test_watcher.py`), but bridging Razorpay's raw
payload fields (amount, card network, email) into the full 60-feature
vector the model expects (C1-C14 velocity signals, D1-D15 time-deltas,
graph-proxy frequencies) requires an aggregated feature store built from
transaction history in real time. That's a separate, real engineering
problem this build doesn't solve -- documented here rather than faked
with a placeholder mapping.

## Graph Builder — live vs. local

`agents/graph_builder.py` tries the live Neo4j AuraDB instance first
(`agents/graph_builder_neo4j.py`, real Cypher, bounded 2-hop traversal
since AuraDB's Free tier has no Graph Data Science library for full
connected-component search) and falls back automatically to a local
networkx graph if Neo4j isn't reachable. The local graph excludes ~60
"hub" addresses shared by an implausible number of transactions (large
fulfillment centers, shared defaults) that otherwise collapse the whole
dataset into one 99%-of-transactions component -- even after that
exclusion, one large component remains (~47% of transactions), which is
reported honestly as general population structure, not treated as ring
membership. The 7,473 small (3-100 txn), fraud-dense components found
after exclusion are the actual ring-detection signal.

Live Neo4j connectivity could not be verified from the sandboxed
development environment (Razorpay's API is blocked by network policy;
Neo4j Aura's hostname doesn't resolve through the sandbox's egress
allowlist) -- `scripts/smoke_test_integrations.py` and
`scripts/load_graph_to_neo4j.py` are meant to be run from a normal
terminal with real internet access.
