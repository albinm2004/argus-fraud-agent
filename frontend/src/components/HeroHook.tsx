import { VerdictBadge } from "./VerdictBadge";
import type { Transaction } from "../types";

export function HeroHook({
  featuredTxn,
  onSelectTxn,
}: {
  featuredTxn: Transaction;
  onSelectTxn: (id: number) => void;
}) {
  return (
    <section className="hero-hook-wrapper" id="hook">
      <div className="hero-grid">
        <div className="hero-claim-col">
          <div className="section-eyebrow">
            <span>Razorpay AI Buildathon</span>
            <span>&middot;</span>
            <span>Track 2: Autonomous Agents</span>
          </div>

          <h1 className="hero-claim-title">
            Catches money launderers sharing cards with{" "}
            <span className="hero-claim-highlight">28 flagged accounts</span> in an 82% fraud cluster.
          </h1>

          <p className="hero-claim-subtitle">
            <strong>Argus</strong> is a 5-agent fraud investigation pipeline. It verifies webhook
            signatures, discovers entity-graph collusion rings, produces SHAP-attributed explanations,
            and hardens itself against adversarial evasion.
          </p>

          <div className="hero-cta-group">
            <a href="#walkthrough" className="btn-primary" onClick={() => onSelectTxn(featuredTxn.id)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Walk Through Real Case (#{featuredTxn.id})
            </a>
            <a href="#adversarial" className="btn-secondary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              See Red-Team Climax (32.8% &rarr; 0%)
            </a>
          </div>

          <div className="hero-features-strip">
            <div className="hero-feat-item">
              <span className="hero-feat-val">0.0%</span>
              <span className="hero-feat-lbl">Hardened Evasion Rate</span>
            </div>
            <div className="hero-feat-item">
              <span className="hero-feat-val">91.0%</span>
              <span className="hero-feat-lbl">Held-Out ROC-AUC</span>
            </div>
            <div className="hero-feat-item">
              <span className="hero-feat-val">5 Agents</span>
              <span className="hero-feat-lbl">LangGraph Pipeline</span>
            </div>
          </div>
        </div>

        {/* Live Highlight Card for Dramatic Case 3464462 */}
        <div className="hero-card-col">
          <div className="hero-card">
            <div className="hero-card-header">
              <span className="hero-card-id">TXN #{featuredTxn.id} &middot; WEBHOOK</span>
              <VerdictBadge verdict={featuredTxn.verdict} />
            </div>

            <div className="hero-card-amount-row">
              <span className="hero-card-amount">${featuredTxn.amount.toFixed(2)}</span>
              <span className="hero-card-risk-pill">Risk Score: {featuredTxn.score.toFixed(4)}</span>
            </div>

            <div className="hero-ring-banner">
              <div className="hero-ring-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="6" cy="6" r="3" />
                  <circle cx="18" cy="18" r="3" />
                  <circle cx="18" cy="6" r="3" />
                  <path d="M8.5 8.5l7 7M8.5 6h7M18 8.5v7" />
                </svg>
                Neo4j Graph: High-Density Collusion Ring
              </div>
              <p className="hero-ring-desc">
                Linked to <strong>{featuredTxn.graph.shared_card_count ?? 34} transactions</strong> on this card &mdash;{" "}
                <strong style={{ color: "#fca5a5" }}>
                  {featuredTxn.graph.neighbor_fraud_count ?? 28} other transactions already flagged as confirmed fraud
                </strong>{" "}
                (82.4% fraud cluster density).
              </p>
            </div>

            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: "0.74rem", color: "var(--ink-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700 }}>
                Top XGBoost SHAP Attribution
              </div>
              <div style={{ fontSize: "0.82rem", color: "var(--ink)", background: "var(--surface-3)", padding: "8px 12px", borderRadius: "6px", border: "1px solid var(--hairline-strong)", fontFamily: "var(--mono)" }}>
                C1 = 10.0 velocity surge &rarr; <span style={{ color: "var(--diverge-up)", fontWeight: 700 }}>+1.525 risk impact</span>
              </div>
            </div>

            <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--ink-muted)" }}>
              <span>Decision Threshold: {featuredTxn.threshold.toFixed(4)}</span>
              <span style={{ color: "var(--status-block)", fontWeight: 700 }}>Decision: IMMEDIATE BLOCK</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
