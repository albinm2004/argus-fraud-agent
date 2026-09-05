import type { Metrics } from "../types";

export function HeroMetrics({ metrics }: { metrics: Metrics }) {
  const { baseline, hardened } = metrics;
  const recallDelta = (hardened.recall - baseline.recall) * 100;
  const evasionDelta = (baseline.evasion_success_rate - hardened.evasion_success_rate) * 100;

  return (
    <>
      <div className="metric-row">
        <div className="metric-tile">
          <div className="label">Recall (held-out)</div>
          <div className="value">{(hardened.recall * 100).toFixed(1)}%</div>
          <div className={`delta ${recallDelta >= 0 ? "up" : "down"}`}>
            {recallDelta >= 0 ? "+" : ""}
            {recallDelta.toFixed(1)}pt vs baseline
          </div>
        </div>
        <div className="metric-tile">
          <div className="label">Precision (held-out)</div>
          <div className="value">{(hardened.precision * 100).toFixed(1)}%</div>
        </div>
        <div className="metric-tile">
          <div className="label">ROC-AUC</div>
          <div className="value">{hardened.roc_auc.toFixed(3)}</div>
        </div>
        <div className="metric-tile">
          <div className="label">Adversarial evasion rate</div>
          <div className="value">{(hardened.evasion_success_rate * 100).toFixed(0)}%</div>
          <div className="delta up">+{evasionDelta.toFixed(1)}pt improvement</div>
        </div>
      </div>
      <div className="metric-caption">
        Held-out metrics: docs/results.md · Adversarial hardening: docs/hardening_results.md
        (evasion rate scoped to the tested perturbation family, not a general robustness claim)
      </div>
    </>
  );
}
