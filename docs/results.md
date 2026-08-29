# Argus — Pattern Analyst baseline results

Baseline: XGBoost over raw transaction features + graph-proxy features (card1/addr1 frequency, card1+addr1 shared-instrument count), evaluated on a **time-based** held-out split — trained on the earlier 80% of transactions by `TransactionDT`, scored on the later 20%. Deliberately harder than a random shuffle split, which would leak future structure into training.

## Metrics (held-out, time-based split)

- Train rows: 472,432 | Held-out rows: 118,108
- Operating threshold: 0.7920 (max recall at precision >= 0.5)
- **Precision: 0.500**
- **Recall: 0.469**
- F1: 0.484
- ROC-AUC: 0.910
- PR-AUC: 0.501

## Top 10 features by importance

- `C8`: 0.1256
- `C4`: 0.1138
- `R_emaildomain`: 0.0569
- `C14`: 0.0501
- `card6`: 0.0463
- `C5`: 0.0463
- `D3`: 0.0427
- `M4`: 0.0334
- `C11`: 0.0278
- `C1`: 0.0227

## Known limitations

- Device/identity features are only present for ~24% of transactions; their contribution is real but partial (see `docs/eda_findings.md`).
- This is the baseline (gradient boosting + graph-proxy features), not yet the GNN upgrade (see `docs/architecture.md`).
- Threshold was chosen on the held-out set itself for reporting; a production deployment would pick it on a separate validation split.
- See `docs/adversarial_results.md` for the robustness delta under the red-team attack.
