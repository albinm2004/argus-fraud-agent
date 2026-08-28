"""Adversarial Red-Team Agent — attacks the Analyst's own model.

TODO (Day 4 — protect this day, it's the differentiator):
- Port the evasion technique from the CAPTCHA hardening project
  (CNN + CLIP-similarity loss style perturbation) to the tabular/graph
  fraud features here.
- Measure precision/recall before vs. after adversarial perturbation.
- Report the robustness delta — this becomes the pitch's headline metric
  alongside the base precision/recall.
"""


def evaluate_robustness(model, held_out_set) -> dict:
    """Returns {"pre_attack": {...}, "post_attack": {...}, "delta": {...}}"""
    raise NotImplementedError
