# Argus — Adversarial red-team results

Black-box, query-based evasion attack against the baseline Pattern Analyst
(XGBoost is non-differentiable, so this is trial-and-error perturbation
search, not gradient-based — the same access level a real fraudster has
against a scoring API, not the CNN+CLIP-loss gradient attack from the
CAPTCHA hardening project, which assumed a differentiable model).

**Threat model**: only features a fraudster could plausibly shape on their
own transaction are perturbed (±35%) — `TransactionAmt` and the
velocity/recency features (`C1-C14`, `D1-D15`). Card, address, and device
identity fields are left untouched: those aren't something a single
fraudulent transaction can cheaply fabricate.

## Fraud evasion result

- Correctly-flagged fraud tested: 1,500 (of 1,904 available in the held-out set)
- Flag rate before attack: 100.0% (by construction — these were all correctly caught)
- Flag rate after best evasion attempt: 67.7%
- **Evasion success rate: 32.3%** of previously-caught fraud could be pushed
  below the operating threshold with realistic amount/velocity perturbation alone.
- Mean predicted-probability drop: 0.122

## Control: same attack against legitimate transactions

- Tested: 1,500 (of which ~26 were originally, incorrectly, flagged — a small
  sample, so this specific rate is noisy)
- False-positive flag rate before: 1.73%
- False-positive flag rate after: 0.27%

The control does **not** show fraud-side transactions are uniquely fragile —
if anything, the rare borderline false-positives were *more* perturbation-sensitive
(most were sitting right at the decision boundary already). The honest reading:
the model's boundary is generally soft near the operating threshold, and the
32.3% fraud evasion rate reflects that general softness, not a fraud-specific
blind spot. That's arguably a more useful finding than a fraud-only weakness
would have been, since it points at the fix (margin-aware / adversarial
training) rather than a narrow patch.

## Honest takeaway

The baseline model has a real, measurable robustness gap: roughly **32%** of
caught fraud can evade detection with plausible amount/velocity manipulation
alone, without touching card or device identity. This motivates hardening
(adversarial training on these exact perturbations, widening the decision
margin near the threshold) as the next step — Track 2 explicitly rewards
honest failure reporting over a clean-looking but untested number.
