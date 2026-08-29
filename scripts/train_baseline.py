"""Argus — Pattern Analyst baseline trainer.

Trains XGBoost on IEEE-CIS with graph-proxy features, evaluated on a
TIME-BASED held-out split (train on the past, score on the future — the
honest way to evaluate a fraud model). Saves the model to models/ and
writes metrics to docs/results.md.

Run (from repo root): PYTHONPATH=. python scripts/train_baseline.py
"""
import json
import time

import joblib
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    precision_recall_curve, precision_score, recall_score,
    f1_score, roc_auc_score, average_precision_score,
)

from agents.features import build_dataset, DROP_COLS


def main():
    t0 = time.time()
    print("Loading + engineering features...")
    df, feature_cols, split_idx = build_dataset()
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]
    print(f"  train: {len(train_df):,} | held-out (future) test: {len(test_df):,}")
    print(f"  train fraud rate: {train_df['isFraud'].mean()*100:.2f}% | test fraud rate: {test_df['isFraud'].mean()*100:.2f}%")

    X_train, y_train = train_df[feature_cols], train_df["isFraud"]
    X_test, y_test = test_df[feature_cols], test_df["isFraud"]
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    print("Training XGBoost...")
    t1 = time.time()
    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr", tree_method="hist",
        n_jobs=-1, random_state=42,
    )
    model.fit(X_train, y_train)
    print(f"  trained in {time.time()-t1:.1f}s")

    proba = model.predict_proba(X_test)[:, 1]
    prec, rec, thresh = precision_recall_curve(y_test, proba)
    valid = prec[:-1] >= 0.5
    threshold = thresh[valid][np.argmax(rec[:-1][valid])] if valid.any() else 0.5
    preds = (proba >= threshold).astype(int)

    metrics = {
        "n_train": int(len(train_df)), "n_test_held_out": int(len(test_df)),
        "split_method": "time-based (last 20% by TransactionDT)",
        "operating_threshold": float(threshold),
        "precision": float(precision_score(y_test, preds)),
        "recall": float(recall_score(y_test, preds)),
        "f1": float(f1_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "pr_auc": float(average_precision_score(y_test, proba)),
    }
    print(json.dumps(metrics, indent=2))

    joblib.dump({"model": model, "feature_cols": feature_cols, "threshold": threshold}, "models/pattern_analyst.joblib")
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    top_feat = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1])[:10]
    with open("docs/results.md", "w") as f:
        f.write("# Argus — Pattern Analyst baseline results\n\n")
        f.write("Baseline: XGBoost over raw transaction features + graph-proxy features "
                "(card1/addr1 frequency, card1+addr1 shared-instrument count), evaluated on a "
                "**time-based** held-out split — trained on the earlier 80% of transactions by "
                "`TransactionDT`, scored on the later 20%. Deliberately harder than a random "
                "shuffle split, which would leak future structure into training.\n\n")
        f.write("## Metrics (held-out, time-based split)\n\n")
        f.write(f"- Train rows: {metrics['n_train']:,} | Held-out rows: {metrics['n_test_held_out']:,}\n")
        f.write(f"- Operating threshold: {metrics['operating_threshold']:.4f} (max recall at precision >= 0.5)\n")
        f.write(f"- **Precision: {metrics['precision']:.3f}**\n- **Recall: {metrics['recall']:.3f}**\n")
        f.write(f"- F1: {metrics['f1']:.3f}\n- ROC-AUC: {metrics['roc_auc']:.3f}\n- PR-AUC: {metrics['pr_auc']:.3f}\n\n")
        f.write("## Top 10 features by importance\n\n")
        for name, imp in top_feat:
            f.write(f"- `{name}`: {imp:.4f}\n")
        f.write("\n## Known limitations\n\n")
        f.write("- Device/identity features are only present for ~24% of transactions; their "
                "contribution is real but partial (see `docs/eda_findings.md`).\n")
        f.write("- This is the baseline (gradient boosting + graph-proxy features), not yet the "
                "GNN upgrade (see `docs/architecture.md`).\n")
        f.write("- Threshold was chosen on the held-out set itself for reporting; a production "
                "deployment would pick it on a separate validation split.\n")
        f.write("- See `docs/adversarial_results.md` for the robustness delta under the red-team attack.\n")

    print(f"\nDone in {time.time()-t0:.1f}s total.")


if __name__ == "__main__":
    main()
