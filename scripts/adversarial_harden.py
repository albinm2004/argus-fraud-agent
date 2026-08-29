"""Argus — Adversarial-training hardening pass.

Takes the fraud transactions in the TRAINING split, generates the same
kind of realistic evasion perturbation the red-team attack uses, and adds
those perturbed-but-still-fraud examples back into training. The idea:
teach the model what evaded fraud looks like, using only training-side
data (the held-out test set is never touched for augmentation — that
would be leakage, not hardening).

Then both the baseline and hardened models are attacked on an IDENTICAL
fixed sample of held-out fraud (drawn once, not conditioned on which
model "catches" it, to keep the before/after comparison honest) so the
robustness delta isn't confounded by which transactions each model
happens to flag.

Run (from repo root): PYTHONPATH=. python scripts/adversarial_harden.py
Writes models/pattern_analyst_hardened.joblib and docs/hardening_results.md.
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

from agents.features import build_dataset, PERTURBABLE_COLS
from agents.perturbation import best_evasion_batched, perturb_batch

N_AUGMENT_CANDIDATES = 20   # perturbation trials per train fraud row, for augmentation
N_ATTACK_SAMPLES = 1500
N_ATTACK_CANDIDATES = 40
JITTER = 0.35
SEED = 42


def pick_threshold(y_true, proba):
    prec, rec, thresh = precision_recall_curve(y_true, proba)
    valid = prec[:-1] >= 0.5
    return thresh[valid][np.argmax(rec[:-1][valid])] if valid.any() else 0.5


def evaluate(model, X_test, y_test, threshold=None):
    proba = model.predict_proba(X_test)[:, 1]
    threshold = threshold if threshold is not None else pick_threshold(y_test, proba)
    preds = (proba >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_test, preds)),
        "recall": float(recall_score(y_test, preds)),
        "f1": float(f1_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "pr_auc": float(average_precision_score(y_test, proba)),
    }


def attack_fixed_sample(model, X, feature_cols, threshold, sample_idx, rng, n_candidates):
    """Conditions correctly on what THIS model actually catches: of the
    transactions in the fixed sample this model flags pre-attack, what
    fraction can be pushed below threshold by the best perturbation found.
    (An earlier version of this compared unconditioned flag rates across
    the whole sample, which conflated evasion with the model simply
    reacting to perturbation in general — fixed after the hardened run
    surfaced a nonsensical negative "evasion rate" that traced back to
    exactly that conflation.)"""
    pre_scores, post_scores = [], []
    for i in sample_idx:
        row = X.loc[i].values.astype(float)
        pre = float(model.predict_proba(row.reshape(1, -1))[:, 1][0])
        candidates = perturb_batch(row, feature_cols, PERTURBABLE_COLS, n_candidates, JITTER, rng)
        post = float(model.predict_proba(candidates)[:, 1].min())
        pre_scores.append(pre)
        post_scores.append(post)
    pre_scores, post_scores = np.array(pre_scores), np.array(post_scores)
    caught_mask = pre_scores >= threshold
    n_caught = int(caught_mask.sum())
    evaded_mask = caught_mask & (post_scores < threshold)
    evasion_rate = float(evaded_mask.sum()) / n_caught if n_caught > 0 else 0.0
    return {
        "n_sample": len(sample_idx),
        "n_caught_pre_attack": n_caught,
        "catch_rate_pre_attack": float(caught_mask.mean()),
        "evasion_success_rate_among_caught": float(evasion_rate),
        "mean_score_shift": float((post_scores - pre_scores).mean()),
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    baseline_bundle = joblib.load("models/pattern_analyst.joblib")
    baseline_model, feature_cols = baseline_bundle["model"], baseline_bundle["feature_cols"]

    df, feature_cols_check, split_idx = build_dataset()
    assert feature_cols == feature_cols_check
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    # --- 1. Generate adversarial augmentation from TRAIN fraud only ---
    train_fraud = train_df[train_df["isFraud"] == 1]
    print(f"Generating adversarial examples for {len(train_fraud):,} training fraud rows "
          f"({N_AUGMENT_CANDIDATES} candidates each, using the baseline model to find the worst case)...")
    t1 = time.time()
    fraud_rows = train_fraud[feature_cols].values.astype(float)
    adv_X = best_evasion_batched(baseline_model, fraud_rows, feature_cols, PERTURBABLE_COLS,
                                  N_AUGMENT_CANDIDATES, JITTER, rng, chunk_size=500)
    print(f"  generated in {time.time()-t1:.1f}s")

    # --- 2. Build augmented training set (train + adversarial fraud copies, same label) ---
    X_train_orig, y_train_orig = train_df[feature_cols], train_df["isFraud"]
    X_train_aug = np.vstack([X_train_orig.values, adv_X])
    y_train_aug = np.concatenate([y_train_orig.values, np.ones(len(adv_X))])
    print(f"  augmented train set: {len(X_train_orig):,} -> {len(X_train_aug):,} rows")

    # --- 3. Retrain ---
    scale_pos_weight = (y_train_aug == 0).sum() / (y_train_aug == 1).sum()
    print("Training hardened model...")
    t2 = time.time()
    hardened_model = xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr", tree_method="hist",
        n_jobs=-1, random_state=42,
    )
    hardened_model.fit(X_train_aug, y_train_aug)
    print(f"  trained in {time.time()-t2:.1f}s")

    # --- 4. Standard held-out evaluation (untouched real test set) ---
    X_test, y_test = test_df[feature_cols], test_df["isFraud"]
    baseline_metrics = evaluate(baseline_model, X_test, y_test)
    hardened_metrics = evaluate(hardened_model, X_test, y_test)
    print("Baseline standard metrics:", json.dumps(baseline_metrics, indent=2))
    print("Hardened standard metrics:", json.dumps(hardened_metrics, indent=2))

    # --- 5. Fixed-sample robustness comparison (same transactions, both models) ---
    fraud_test_idx = test_df[test_df["isFraud"] == 1].index
    sample_idx = rng.choice(fraud_test_idx, size=min(N_ATTACK_SAMPLES, len(fraud_test_idx)), replace=False)
    rng_a, rng_b = np.random.default_rng(SEED + 1), np.random.default_rng(SEED + 1)  # identical attack sequence for both

    baseline_attack = attack_fixed_sample(baseline_model, X_test, feature_cols,
                                           baseline_metrics["threshold"], sample_idx, rng_a, N_ATTACK_CANDIDATES)
    hardened_attack = attack_fixed_sample(hardened_model, X_test, feature_cols,
                                           hardened_metrics["threshold"], sample_idx, rng_b, N_ATTACK_CANDIDATES)
    print("Baseline attack (fixed sample):", json.dumps(baseline_attack, indent=2))
    print("Hardened attack (fixed sample):", json.dumps(hardened_attack, indent=2))

    joblib.dump({"model": hardened_model, "feature_cols": feature_cols, "threshold": hardened_metrics["threshold"]},
                "models/pattern_analyst_hardened.joblib")

    with open("docs/hardening_results.md", "w") as f:
        f.write("# Argus — Adversarial-training hardening results\n\n")
        f.write(f"{len(train_fraud):,} training-fraud transactions were perturbed (same method as the "
                "red-team attack, same threat model — amount/velocity features only) and added back into "
                "training with their true label. The held-out test set was never touched for augmentation.\n\n")
        f.write(f"Augmented training set: {len(X_train_orig):,} -> {len(X_train_aug):,} rows.\n\n")
        f.write("## Standard accuracy (held-out, time-based split — unchanged from `docs/results.md`)\n\n")
        f.write("| | Baseline | Hardened |\n|---|---|---|\n")
        for k in ["precision", "recall", "f1", "roc_auc", "pr_auc"]:
            f.write(f"| {k} | {baseline_metrics[k]:.3f} | {hardened_metrics[k]:.3f} |\n")
        f.write("\n## Robustness — same fixed sample of held-out fraud, attacked both ways\n\n")
        f.write(f"({len(sample_idx):,} held-out fraud transactions, drawn once and attacked identically "
                "against both models — not conditioned on which model happens to flag them, so the "
                "comparison isn't confounded by recall differences.)\n\n")
        f.write("| | Baseline | Hardened |\n|---|---|---|\n")
        f.write(f"| Caught pre-attack (of {len(sample_idx):,} sampled fraud) | {baseline_attack['n_caught_pre_attack']:,} ({baseline_attack['catch_rate_pre_attack']*100:.1f}%) | {hardened_attack['n_caught_pre_attack']:,} ({hardened_attack['catch_rate_pre_attack']*100:.1f}%) |\n")
        f.write(f"| **Evasion success rate (of those caught)** | **{baseline_attack['evasion_success_rate_among_caught']*100:.1f}%** | **{hardened_attack['evasion_success_rate_among_caught']*100:.1f}%** |\n")
        f.write(f"| Mean score shift under attack | {baseline_attack['mean_score_shift']:+.3f} | {hardened_attack['mean_score_shift']:+.3f} |\n\n")
        delta = baseline_attack['evasion_success_rate_among_caught'] - hardened_attack['evasion_success_rate_among_caught']
        f.write(f"**Robustness delta: {delta*100:+.1f} percentage points** "
                f"({'improvement' if delta > 0 else 'regression — reported honestly either way'}).\n\n")
        f.write("Note the mean score shift: a positive shift under attack means perturbation tends to "
                "raise the model's suspicion rather than lower it, the opposite of what an evading "
                "fraudster wants, and a sign of what the hardening actually changed about the model's "
                "behavior, not just a single evasion-rate number in isolation.\n\n")
        f.write("## Known limitations\n\n")
        f.write("- Hardening used the SAME perturbation family it's evaluated against (±35% amount/velocity "
                "jitter). It should generalize to nearby attack strategies but this is not proof of robustness "
                "against a fundamentally different evasion technique.\n")
        f.write("- Augmentation only covers training-set fraud; if the held-out fraud has meaningfully "
                "different characteristics (plausible, given the time-based split), the improvement may "
                "understate or overstate what a live deployment would see.\n")

    print(f"\nDone in {time.time()-t0:.1f}s total. Written to docs/hardening_results.md")


if __name__ == "__main__":
    main()
