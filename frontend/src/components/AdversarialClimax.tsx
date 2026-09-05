import type { Metrics, Transaction } from "../types";
import { RedTeamChart } from "./charts/RedTeamChart";

export function AdversarialClimax({
  metrics,
  transactions,
}: {
  metrics: Metrics;
  transactions: Transaction[];
}) {
  const { baseline, hardened, attack_sample_size } = metrics;
  const basePct = baseline.evasion_success_rate * 100;
  const hardPct = hardened.evasion_success_rate * 100;

  return (
    <section className="story-section" id="adversarial">
      <div className="section-header">
        <div className="section-eyebrow">
          <span>The Differentiator</span>
          <span>&middot;</span>
          <span>Adversarial Red-Teaming & Hardening ({attack_sample_size.toLocaleString()} attacks)</span>
        </div>
        <h2 className="section-title">We tried to beat our own model &mdash; then hardened it</h2>
        <p className="section-desc">
          Most fraud models are tested statically. But real fraudsters observe threshold boundaries
          and perturb their own transaction amounts, frequencies, and velocity signals to sneak under
          the radar. We launched a black-box attack on {attack_sample_size.toLocaleString()} held-out fraud cases to test resilience.
        </p>
      </div>

      <div className="adversarial-hero-box">
        {/* Battle Arena Side-by-Side Comparison */}
        <div className="adversarial-battle-grid">
          {/* Baseline Card */}
          <div className="battle-card baseline">
            <div className="battle-tag crit">Baseline XGBoost Model</div>
            <div className="battle-rate crit">{basePct.toFixed(1)}%</div>
            <div style={{ fontSize: "0.86rem", fontWeight: 700, color: "var(--status-block)", marginBottom: 8 }}>
              Evasion Success Rate (237 of 722 evaded)
            </div>
            <p className="battle-desc">
              When fraudsters nudged amount and velocity features by &plusmn;35%, nearly 1 in 3
              previously blocked frauds slipped past the decision threshold.
            </p>
            <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--surface-3)", borderRadius: "var(--radius-sm)", fontSize: "0.76rem", color: "var(--ink-secondary)", fontFamily: "var(--mono)" }}>
              Mean Score Shift: <span style={{ color: "var(--status-block)", fontWeight: 700 }}>-0.156</span> (Suspicion lowered)
            </div>
          </div>

          {/* VS Divider & Delta Badge */}
          <div className="battle-vs-divider">
            <div className="delta-badge">+32.8% Robustness Delta</div>
            <span style={{ fontSize: "0.74rem", color: "var(--ink-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>
              At cost of only 0.2% recall
            </span>
          </div>

          {/* Hardened Card */}
          <div className="battle-card hardened">
            <div className="battle-tag good">Hardened Argus Model</div>
            <div className="battle-rate good">{hardPct.toFixed(1)}%</div>
            <div style={{ fontSize: "0.86rem", fontWeight: 700, color: "var(--status-allow)", marginBottom: 8 }}>
              Evasion Success Rate (0 of 714 evaded)
            </div>
            <p className="battle-desc">
              Retrained with adversarial sample augmentation (16,599 perturbed fraud instances).
              Zero fraud cases evaded the hardened model on the tested attack family.
            </p>
            <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--surface-3)", borderRadius: "var(--radius-sm)", fontSize: "0.76rem", color: "var(--status-allow)", fontWeight: 700 }}>
              Mean Score Shift: <span style={{ color: "var(--status-allow)", fontWeight: 700 }}>+0.347</span> (Suspicion raised!)
            </div>
          </div>
        </div>

        {/* Why the Score Shift Matters */}
        <div className="shift-explainer-box">
          <strong style={{ color: "var(--ink)" }}>Why the mean score shift is the key signal:</strong> In the baseline model, adversarial feature perturbation pushed scores downward (mean shift: &minus;0.156). In the hardened model, feature perturbation causes the model to become <em>more</em> suspicious (mean shift: +0.347), turning would-be evasions into confident hard blocks.
        </div>

        {/* Trajectory Chart on 15 Real Borderline Cases */}
        <div style={{ marginTop: 28 }}>
          <RedTeamChart transactions={transactions} />
        </div>

      </div>
    </section>
  );
}
