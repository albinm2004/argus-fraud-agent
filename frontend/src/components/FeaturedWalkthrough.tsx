import { useState } from "react";
import type { Transaction } from "../types";
import { VerdictBadge } from "./VerdictBadge";
import { ScoreScale } from "./ScoreScale";
import { EvidenceBar } from "./EvidenceBar";

const ARCHETYPES: { id: number; label: string; badge: string; desc: string }[] = [
  {
    id: 3464462,
    label: "Fraud Ring Collusion",
    badge: "82% Fraud Ring",
    desc: "Txn #3464462 ($86.69) shares card with 34 accounts, 28 already confirmed fraud.",
  },
  {
    id: 3481071,
    label: "Massive Card Hub",
    badge: "376 Shared Links",
    desc: "Txn #3481071 ($44.27) linked to 376 accounts via shared card, 88 confirmed fraud.",
  },
  {
    id: 3520655,
    label: "Adversarial Attack Target",
    badge: "Perturbed & Blocked",
    desc: "Txn #3520655 ($117.00) pre-attack 0.712 flag shifted to 0.9883 block under hardening.",
  },
  {
    id: 3537527,
    label: "Honest Miss (Transparency)",
    badge: "Recall Case",
    desc: "Txn #3537527 ($50.00) score 0.558 allowed despite actual fraud — honest 47% recall in practice.",
  },
];

export function FeaturedWalkthrough({
  transactions,
  selectedTxn,
  onSelectTxn,
}: {
  transactions: Transaction[];
  selectedTxn: Transaction;
  onSelectTxn: (id: number) => void;
}) {
  const [showFeed, setShowFeed] = useState(false);
  const [filterVerdict, setFilterVerdict] = useState<string>("all");
  const [filterGraph, setFilterGraph] = useState<boolean>(false);
  const [filterRedTeam, setFilterRedTeam] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filteredTransactions = transactions.filter((t) => {
    if (filterVerdict !== "all" && t.verdict !== filterVerdict) return false;
    if (filterGraph && (!t.graph.found || (t.graph.neighbor_fraud_count ?? 0) === 0)) return false;
    if (filterRedTeam && t.red_team === null) return false;
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      return (
        t.id.toString().includes(q) ||
        t.amount.toString().includes(q) ||
        t.verdict.toLowerCase().includes(q) ||
        t.actual.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const isFraud = selectedTxn.actual === "fraud";
  const neighborFraud = selectedTxn.graph.neighbor_fraud_count ?? selectedTxn.graph.other_fraud_in_component ?? 0;
  const sharedCards = selectedTxn.graph.shared_card_count ?? 0;
  const sharedAddrs = selectedTxn.graph.shared_addr_count ?? 0;

  return (
    <section className="story-section" id="walkthrough">
      <div className="section-header">
        <div className="section-eyebrow">
          <span>Proof by Example</span>
          <span>&middot;</span>
          <span>End-to-End Investigation Walkthrough</span>
        </div>
        <h2 className="section-title">Walk a real transaction through all five agents</h2>
        <p className="section-desc">
          Instead of looking at abstract confusion matrices first, inspect how Argus processes,
          correlates, explains, and renders a verdict for an individual payment webhook in real time.
        </p>
      </div>

      <div className="featured-showcase-box">
        {/* Archetype Selector */}
        <div className="archetype-selector">
          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--ink-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Featured Archetypes:
          </span>
          {ARCHETYPES.map((arch) => {
            const isActive = selectedTxn.id === arch.id;
            return (
              <button
                key={arch.id}
                className={`archetype-btn ${isActive ? "active" : ""}`}
                onClick={() => onSelectTxn(arch.id)}
              >
                <span>{arch.label}</span>
                <span style={{ fontSize: "0.68rem", opacity: 0.85, background: "rgba(255,255,255,0.1)", padding: "1px 6px", borderRadius: 4 }}>
                  {arch.badge}
                </span>
              </button>
            );
          })}
        </div>

        {/* Overview Bar of Active Transaction */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14, background: "var(--surface-2)", padding: "14px 18px", borderRadius: "var(--radius-md)", border: "1px solid var(--hairline)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: "1.05rem" }}>
              TXN #{selectedTxn.id}
            </span>
            <span style={{ fontSize: "1.2rem", fontWeight: 800, fontFamily: "var(--mono)", color: "var(--ink)" }}>
              ${selectedTxn.amount.toFixed(2)}
            </span>
            <VerdictBadge verdict={selectedTxn.verdict} />
            <span style={{ fontSize: "0.78rem", padding: "3px 9px", borderRadius: 6, background: isFraud ? "var(--status-block-bg)" : "var(--status-allow-bg)", color: isFraud ? "var(--status-block)" : "var(--status-allow)", border: `1px solid ${isFraud ? "var(--status-block-border)" : "var(--status-allow-border)"}`, fontWeight: 700 }}>
              Ground Truth: {isFraud ? "CONFIRMED FRAUD" : "LEGITIMATE"}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: "0.8rem", color: "var(--ink-secondary)" }}>
              Score: <strong style={{ color: "var(--ink)", fontFamily: "var(--mono)" }}>{selectedTxn.score.toFixed(4)}</strong> / Threshold: <strong style={{ fontFamily: "var(--mono)" }}>{selectedTxn.threshold.toFixed(4)}</strong>
            </span>
          </div>
        </div>

        {/* 4-Step Pipeline Breakdown Grid */}
        <div className="walkthrough-steps-grid">
          {/* Step 1: Watcher */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-num">Step 1 &middot; Watcher</span>
              <span className="step-status-tag ok">✓ Verified</span>
            </div>
            <div className="step-title">Webhook Signature</div>
            <div className="step-subtitle">HMAC-SHA256 Payload Check</div>
            <div className="step-body-content">
              <div className="step-metric-box">
                <div className="step-metric-val">&lt; 1 ms</div>
                <div className="step-metric-lbl">Verification Latency</div>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--ink-secondary)", lineHeight: 1.5 }}>
                Signature header matches secret. Event parsed into normalized schema with timestamp and currency normalization.
              </p>
            </div>
          </div>

          {/* Step 2: Graph Builder */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-num">Step 2 &middot; Graph</span>
              <span className={`step-status-tag ${neighborFraud > 0 ? "crit" : "ok"}`}>
                {neighborFraud > 0 ? `${neighborFraud} Frauds in Cluster` : "Isolated"}
              </span>
            </div>
            <div className="step-title">Entity Ring Analysis</div>
            <div className="step-subtitle">Neo4j AuraDB &middot; Shared Nodes</div>
            <div className="step-body-content">
              <div className="step-metric-box">
                <div className="step-metric-val" style={{ color: neighborFraud > 0 ? "var(--status-block)" : "var(--status-allow)" }}>
                  {sharedCards} Card / {sharedAddrs} Addr
                </div>
                <div className="step-metric-lbl">Connected Entities</div>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--ink-secondary)", lineHeight: 1.5 }}>
                {neighborFraud > 0
                  ? `High-risk cluster! This account shares payment instruments with ${neighborFraud} confirmed fraud cases.`
                  : "No suspicious entity-sharing detected in the 1-hop or 2-hop neighborhood."}
              </p>
            </div>
          </div>

          {/* Step 3: Pattern Analyst */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-num">Step 3 &middot; ML Scorer</span>
              <span className={`step-status-tag ${selectedTxn.score >= selectedTxn.threshold ? "crit" : "ok"}`}>
                Score: {selectedTxn.score.toFixed(3)}
              </span>
            </div>
            <div className="step-title">XGBoost + SHAP</div>
            <div className="step-subtitle">Feature Attributions</div>
            <div className="step-body-content">
              <ScoreScale score={selectedTxn.score} threshold={selectedTxn.threshold} verdict={selectedTxn.verdict} />
              
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: "0.7rem", color: "var(--ink-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: 6 }}>
                  Top SHAP Evidence (Native contribs):
                </div>
                {selectedTxn.evidence.slice(0, 3).map((line, idx) => (
                  <EvidenceBar key={idx} line={line} />
                ))}
              </div>
            </div>
          </div>

          {/* Step 4: Verdict & Red-Team */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-num">Step 4 &middot; Decision</span>
              <span className={`step-status-tag ${selectedTxn.verdict === "block" ? "crit" : selectedTxn.verdict === "flag" ? "warn" : "ok"}`}>
                {selectedTxn.verdict.toUpperCase()}
              </span>
            </div>
            <div className="step-title">Verdict & Audit</div>
            <div className="step-subtitle">Autonomous Policy Execution</div>
            <div className="step-body-content">
              <div className="step-metric-box">
                <div className="step-metric-val">
                  {selectedTxn.verdict === "block" ? "Blocked" : selectedTxn.verdict === "flag" ? "Flagged" : "Approved"}
                </div>
                <div className="step-metric-lbl">
                  Policy: {selectedTxn.score >= 0.75 ? "Score >= 0.75" : selectedTxn.score >= 0.70 ? "0.70 <= Score < 0.75" : "Score < 0.70"}
                </div>
              </div>
              
              {selectedTxn.red_team && (
                <div style={{ background: "var(--surface-3)", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--accent-border)", marginTop: 4 }}>
                  <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--accent-bright)" }}>
                    🛡️ Red-Team Perturbation Result:
                  </div>
                  <div style={{ fontSize: "0.75rem", fontFamily: "var(--mono)", color: "var(--ink)" }}>
                    Pre: {selectedTxn.red_team.pre.toFixed(3)} &rarr; Post: {selectedTxn.red_team.post.toFixed(3)} ({selectedTxn.red_team.evaded ? "Evaded" : "Defense Held"})
                  </div>
                </div>
              )}

              <p style={{ fontSize: "0.76rem", color: "var(--ink-secondary)", lineHeight: 1.45, marginTop: 4 }}>
                Verdict sealed and logged to rotating tamper-proof audit trail.
              </p>
            </div>
          </div>
        </div>

        {/* Expandable 300-Transaction Explorer Drawer */}
        <button
          className="feed-drawer-trigger"
          onClick={() => setShowFeed((prev) => !prev)}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M9 21V9" />
            </svg>
            <strong>{showFeed ? "Hide" : "Explore"} All 300 Scored Transactions</strong> ({transactions.length} rows loaded from pipeline)
          </span>
          <span>{showFeed ? "▲ Collapse Feed" : "▼ Expand & Pick Any Transaction"}</span>
        </button>

        {showFeed && (
          <div style={{ marginTop: 18, padding: 18, background: "var(--surface-2)", borderRadius: "var(--radius-lg)", border: "1px solid var(--hairline)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 14 }}>
              {/* Verdict Filter Pills */}
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {["all", "block", "flag", "allow"].map((v) => (
                  <button
                    key={v}
                    className={`filter-pill ${filterVerdict === v ? "active" : ""}`}
                    onClick={() => setFilterVerdict(v)}
                  >
                    {v.toUpperCase()} ({v === "all" ? transactions.length : transactions.filter((t) => t.verdict === v).length})
                  </button>
                ))}
              </div>

              {/* Special Toggles */}
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  className={`filter-pill ${filterGraph ? "active" : ""}`}
                  onClick={() => setFilterGraph((prev) => !prev)}
                >
                  🕸️ Has Graph Collusion
                </button>
                <button
                  className={`filter-pill ${filterRedTeam ? "active" : ""}`}
                  onClick={() => setFilterRedTeam((prev) => !prev)}
                >
                  🛡️ Red-Team Tested (15)
                </button>
                <input
                  type="text"
                  placeholder="Search ID / Amount..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    background: "var(--surface-3)",
                    border: "1px solid var(--hairline-strong)",
                    color: "var(--ink)",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    fontSize: "0.8rem",
                    outline: "none",
                    fontFamily: "var(--mono)",
                  }}
                />
              </div>
            </div>

            {/* Table */}
            <div className="feed-table-wrap" style={{ maxHeight: "380px" }}>
              <table className="feed-table">
                <thead>
                  <tr>
                    <th>Txn ID</th>
                    <th style={{ textAlign: "right" }}>Amount</th>
                    <th style={{ textAlign: "right" }}>Score</th>
                    <th>Verdict</th>
                    <th>Actual</th>
                    <th>Graph Ring</th>
                    <th>Adversarial</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTransactions.map((t) => {
                    const isSel = t.id === selectedTxn.id;
                    const neighborF = t.graph.neighbor_fraud_count ?? 0;
                    return (
                      <tr
                        key={t.id}
                        className={isSel ? "selected" : ""}
                        onClick={() => onSelectTxn(t.id)}
                      >
                        <td style={{ fontFamily: "var(--mono)", fontWeight: isSel ? 700 : 500 }}>
                          #{t.id}
                        </td>
                        <td className="num">${t.amount.toFixed(2)}</td>
                        <td className="num" style={{ fontFamily: "var(--mono)" }}>
                          {t.score.toFixed(3)}
                        </td>
                        <td>
                          <span className="verdict-cell">
                            <VerdictBadge verdict={t.verdict} />
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: "0.76rem", color: t.actual === "fraud" ? "var(--status-block)" : "var(--status-allow)", fontWeight: 600 }}>
                            {t.actual.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          {neighborF > 0 ? (
                            <span style={{ fontSize: "0.74rem", color: "var(--status-block)", fontWeight: 600 }}>
                              🕸️ {neighborF} fraud links
                            </span>
                          ) : (
                            <span style={{ fontSize: "0.74rem", color: "var(--ink-muted)" }}>
                              Clean
                            </span>
                          )}
                        </td>
                        <td>
                          {t.red_team ? (
                            <span style={{ fontSize: "0.74rem", color: "var(--accent-bright)", fontWeight: 600 }}>
                              Tested ({t.red_team.evaded ? "Evaded" : "Held"})
                            </span>
                          ) : (
                            <span style={{ fontSize: "0.74rem", color: "var(--ink-muted)" }}>-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 10, fontSize: "0.74rem", color: "var(--ink-muted)", textAlign: "right" }}>
              Showing {filteredTransactions.length} of {transactions.length} transactions &middot; Click any row to load it into the walkthrough above.
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
