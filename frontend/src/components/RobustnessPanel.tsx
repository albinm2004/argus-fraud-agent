import type { Metrics } from "../types";

export function RobustnessPanel({ metrics }: { metrics: Metrics }) {
  const { baseline, hardened, attack_sample_size } = metrics;
  const basePct = baseline.evasion_success_rate * 100;
  const hardPct = hardened.evasion_success_rate * 100;

  return (
    <div className="panel">
      <h2>Adversarial hardening</h2>
      <p style={{ color: "var(--ink-secondary)", fontSize: "0.88rem", marginTop: -6 }}>
        Black-box, query-based evasion attack ({attack_sample_size.toLocaleString()} held-out
        fraud transactions) &mdash; can a fraudster nudge their own amount/velocity features to
        sneak under the threshold?
      </p>
      <div className="robust-compare">
        <div className="robust-col">
          <h4>Baseline model</h4>
          <div className="robust-bar-row">
            <div className="robust-bar-track">
              <div
                className="robust-bar-fill"
                style={{ width: `${Math.max(basePct, 3)}%`, background: "var(--status-block)" }}
              />
            </div>
            <span className="robust-bar-label" style={{ color: "var(--status-block)" }}>
              {basePct.toFixed(1)}% evaded
            </span>
          </div>
        </div>
        <div className="robust-col">
          <h4>Hardened model</h4>
          <div className="robust-bar-row">
            <div className="robust-bar-track">
              <div
                className="robust-bar-fill"
                style={{ width: `${Math.max(hardPct, 3)}%`, background: "var(--status-allow)" }}
              />
            </div>
            <span className="robust-bar-label" style={{ color: "var(--status-allow)" }}>
              {hardPct.toFixed(1)}% evaded
            </span>
          </div>
        </div>
      </div>
      <h3>What changed</h3>
      <p style={{ color: "var(--ink-secondary)", fontSize: "0.86rem", lineHeight: 1.6 }}>
        Adversarial training on the same perturbation family closed the evasion gap from{" "}
        {basePct.toFixed(1)}% to {hardPct.toFixed(1)}%, at a cost of{" "}
        {((baseline.recall - hardened.recall) * 100).toFixed(1)} points of recall. Scoped
        honestly to the tested perturbation family, not a general robustness claim &mdash; see
        docs/hardening_results.md for the full methodology and known limitations.
      </p>
    </div>
  );
}
