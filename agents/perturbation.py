"""Shared perturbation logic — used by the red-team attack, the hardening
trainer, and the live Red-Team Agent, so all three search the same way."""
import numpy as np


def perturb_batch(base_row, feature_cols, perturbable_cols, n_candidates, jitter, rng):
    """base_row: 1D array matching feature_cols. Returns (n_candidates, n_features)."""
    perturbable_idx = [feature_cols.index(c) for c in perturbable_cols if c in feature_cols]
    batch = np.tile(base_row, (n_candidates, 1)).astype(float)
    for idx in perturbable_idx:
        base = batch[:, idx]
        factors = rng.uniform(1 - jitter, 1 + jitter, size=n_candidates)
        jittered = base * factors
        jittered = np.where(np.abs(base) < 1e-6, rng.uniform(-1, 1, size=n_candidates), jittered)
        batch[:, idx] = jittered
    return batch


def best_evasion(model, base_row, feature_cols, perturbable_cols, n_candidates, jitter, rng):
    """Returns (best_candidate_row, best_score) — the single perturbation
    (among n_candidates) that minimizes the model's predicted probability."""
    candidates = perturb_batch(base_row, feature_cols, perturbable_cols, n_candidates, jitter, rng)
    probs = model.predict_proba(candidates)[:, 1]
    best_i = int(np.argmin(probs))
    return candidates[best_i], float(probs[best_i])


def best_evasion_batched(model, rows, feature_cols, perturbable_cols, n_candidates, jitter, rng, chunk_size=500):
    """Vectorized version of best_evasion for many rows at once — batches
    predict_proba calls across chunk_size rows x n_candidates at a time
    instead of one row per call, which matters at training-set scale.

    rows: (n_rows, n_features) array. Returns (n_rows, n_features) array of
    each row's best (lowest-scoring) perturbation.
    """
    n_rows = rows.shape[0]
    out = np.empty_like(rows, dtype=float)
    for start in range(0, n_rows, chunk_size):
        chunk = rows[start:start + chunk_size]
        n = chunk.shape[0]
        # Build (n * n_candidates, n_features) candidate matrix for the whole chunk.
        all_candidates = np.vstack([
            perturb_batch(chunk[i], feature_cols, perturbable_cols, n_candidates, jitter, rng)
            for i in range(n)
        ])
        probs = model.predict_proba(all_candidates)[:, 1].reshape(n, n_candidates)
        best_idx = probs.argmin(axis=1)
        candidates_3d = all_candidates.reshape(n, n_candidates, -1)
        out[start:start + chunk_size] = candidates_3d[np.arange(n), best_idx]
    return out
