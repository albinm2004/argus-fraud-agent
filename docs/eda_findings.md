# EDA findings — IEEE-CIS Fraud Detection

First pass over the full `train_transaction.csv` + `train_identity.csv`
(590,540 transactions). Reproducible via `python scripts/eda_summary.py`.

## Headline numbers

- **590,540 transactions**, **3.499% fraud rate** (~20,663 fraud rows) —
  enough positive examples for a real held-out precision/recall split.
- **card1**: 13,553 unique values across 590K transactions — cards repeat
  often enough to be a useful graph edge (shared-card linkage).
- **addr1**: 332 unique values, 11.1% missing — usable as a graph edge,
  moderate cardinality (won't collapse into one giant clique).
- **P_emaildomain**: only 59 unique values, 16% missing — too coarse to
  use as a graph edge (e.g. "gmail.com" would connect huge swaths of
  unrelated users into one clique). Keeping it as a **model feature**
  instead of a graph edge.
- **Device signal**: only 24.4% of transactions have a matching identity
  record (where `DeviceType`/`DeviceInfo` live). Real limitation, noted
  honestly rather than papered over — the Graph Builder will treat
  device-linked edges as a *bonus* signal present for roughly 1 in 4
  transactions, not a universal feature.

## Graph Builder implication

Entity graph edges, in order of signal quality:
1. Shared `card1`/`card2` combination — strongest, most direct fraud-ring
   signal (same instrument reused).
2. Shared `addr1`/`addr2` — good secondary signal, right cardinality.
3. Shared `DeviceInfo`/`DeviceType` — valuable but only available for
   ~24% of transactions; treated as a bonus edge, not a required one.
4. `P_emaildomain` — kept as a Pattern Analyst *feature*, not a graph
   edge, because of low cardinality.

## Known limitation (goes in the README)

Only ~1 in 4 transactions carry an identity/device record. Any claim
about device-based fraud-ring detection has to be scoped to that subset
honestly, not silently extrapolated to the full dataset.
