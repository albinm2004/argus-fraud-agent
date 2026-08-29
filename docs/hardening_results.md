# Argus — Adversarial-training hardening results

16,599 training-fraud transactions were perturbed (same method as the red-team attack, same threat model — amount/velocity features only) and added back into training with their true label. The held-out test set was never touched for augmentation.

Augmented training set: 472,432 -> 489,031 rows.

## Standard accuracy (held-out, time-based split — unchanged from `docs/results.md`)

| | Baseline | Hardened |
|---|---|---|
| precision | 0.500 | 0.500 |
| recall | 0.469 | 0.467 |
| f1 | 0.484 | 0.483 |
| roc_auc | 0.910 | 0.905 |
| pr_auc | 0.501 | 0.494 |

## Robustness — same fixed sample of held-out fraud, attacked both ways

(1,500 held-out fraud transactions, drawn once and attacked identically against both models — not conditioned on which model happens to flag them, so the comparison isn't confounded by recall differences.)

| | Baseline | Hardened |
|---|---|---|
| Caught pre-attack (of 1,500 sampled fraud) | 722 (48.1%) | 714 (47.6%) |
| **Evasion success rate (of those caught)** | **32.8%** | **0.0%** |
| Mean score shift under attack | -0.156 | +0.347 |

**Robustness delta: +32.8 percentage points** (improvement).

Note the mean score shift: a positive shift under attack means perturbation tends to raise the model's suspicion rather than lower it, the opposite of what an evading fraudster wants, and a sign of what the hardening actually changed about the model's behavior, not just a single evasion-rate number in isolation.

## Known limitations

- Hardening used the SAME perturbation family it's evaluated against (±35% amount/velocity jitter). It should generalize to nearby attack strategies but this is not proof of robustness against a fundamentally different evasion technique.
- Augmentation only covers training-set fraud; if the held-out fraud has meaningfully different characteristics (plausible, given the time-based split), the improvement may understate or overstate what a live deployment would see.
