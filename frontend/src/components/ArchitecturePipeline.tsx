import { useState } from "react";

interface AgentSpec {
  id: string;
  step: string;
  name: string;
  oneLiner: string;
  latency: string;
  techStack: string;
  resilience: string;
  deepDetails: string;
}

const AGENT_PIPELINE: AgentSpec[] = [
  {
    id: "watcher",
    step: "Stage 1",
    name: "Watcher Agent",
    oneLiner: "Verifies Razorpay webhook HMAC-SHA256 signature and normalizes raw JSON payload.",
    latency: "< 1 ms",
    techStack: "HMAC-SHA256, Pydantic v2",
    resilience: "Rejects tampered requests immediately before reaching downstream agents",
    deepDetails:
      "Performs cryptographic webhook signature verification against razorpay_signature header using shared secret. Normalizes disparate currency codes, timestamps, and customer identifiers into a canonical FraudEvent schema.",
  },
  {
    id: "graph",
    step: "Stage 2",
    name: "Graph Builder",
    oneLiner: "Uncovers shared card and address collusion rings via live Neo4j AuraDB graph.",
    latency: "~18 ms",
    techStack: "Neo4j AuraDB, Cypher, Local Fallback",
    resilience: "Automatic fallback to in-memory graph cache if Neo4j is offline or slow",
    deepDetails:
      "Executes 2-hop Cypher queries to discover shared cards, billing addresses, and prior fraud flags in the same connected component. Filters popular hub addresses to avoid false ring collapsing.",
  },
  {
    id: "analyst",
    step: "Stage 3",
    name: "Pattern Analyst",
    oneLiner: "Evaluates 30+ velocity and graph features using an adversarially trained XGBoost model.",
    latency: "~4 ms",
    techStack: "XGBoost, Native SHAP (pred_contribs)",
    resilience: "Pre-compiled tree booster with zero runtime Python overhead",
    deepDetails:
      "Scores transaction risk using a hardened XGBoost tree ensemble. Computes native per-feature SHAP contributions (pred_contribs=True) in a single inference pass, providing signed attribution without expensive external explainers.",
  },
  {
    id: "redteam",
    step: "Stage 4",
    name: "Red-Team Agent",
    oneLiner: "Perturbs amount and velocity features on borderline cases to simulate live adversary evasion.",
    latency: "~12 ms",
    techStack: "Black-box Query Jitter, Boundary Probe",
    resilience: "Activated selectively for borderline scores (0.65 - 0.75) to conserve latency",
    deepDetails:
      "Simulates an intelligent fraudster attempting to cross the decision boundary by nudging velocity counters and transaction amounts by ±35%. Confirms that the hardened model escalates suspicion rather than lowering it.",
  },
  {
    id: "verdict",
    step: "Stage 5",
    name: "Verdict + Audit",
    oneLiner: "Renders deterministic block/flag/allow decision and signs immutable audit trail.",
    latency: "< 2 ms",
    techStack: "Policy Engine, Rotating Audit Log",
    resilience: "Deterministic fail-safe rules with cryptographic log integrity",
    deepDetails:
      "Applies calibrated risk thresholds (Score >= 0.75 -> BLOCK, 0.70-0.75 -> FLAG, < 0.70 -> ALLOW). Synthesizes natural-language explanations and appends signed audit log receipts for regulatory compliance.",
  },
];

export function ArchitecturePipeline() {
  const [selectedAgent, setSelectedAgent] = useState<AgentSpec>(AGENT_PIPELINE[0]);

  return (
    <section className="story-section" id="architecture">
      <div className="section-header">
        <div className="section-eyebrow">
          <span>Multi-Agent System</span>
          <span>&middot;</span>
          <span>15-Second Scannable Architecture</span>
        </div>
        <h2 className="section-title">Five specialized agents wired as a LangGraph state machine</h2>
        <p className="section-desc">
          Argus is not a sequence of disjointed scripts. Each agent has an isolated responsibility,
          dedicated error boundaries, and deterministic state transitions. Click any stage to inspect.
        </p>
      </div>

      {/* 5-Column Horizontal Pipeline Flow */}
      <div className="arch-grid-5">
        {AGENT_PIPELINE.map((agent) => {
          const isSelected = selectedAgent.id === agent.id;
          return (
            <div
              key={agent.id}
              className={`agent-node-card ${isSelected ? "selected" : ""}`}
              onClick={() => setSelectedAgent(agent)}
            >
              <div className="agent-step-idx">{agent.step}</div>
              <div className="agent-node-name">{agent.name}</div>
              <div className="agent-node-summary">{agent.oneLiner}</div>
              <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.72rem", color: "var(--ink-muted)", borderTop: "1px solid var(--hairline)", paddingTop: 8 }}>
                <span>Latency: {agent.latency}</span>
                <span style={{ color: "var(--accent-bright)", fontWeight: 700 }}>
                  {isSelected ? "● Viewing" : "Inspect →"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Deep Specification Card for Selected Agent */}
      <div className="agent-deep-spec">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div>
            <span style={{ fontSize: "0.72rem", fontWeight: 800, textTransform: "uppercase", color: "var(--accent-bright)", letterSpacing: "0.1em" }}>
              {selectedAgent.step} Specification
            </span>
            <div className="spec-title">{selectedAgent.name}</div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ fontSize: "0.76rem", background: "var(--surface-3)", padding: "4px 10px", borderRadius: 6, border: "1px solid var(--hairline)", fontFamily: "var(--mono)" }}>
              Latency: {selectedAgent.latency}
            </span>
          </div>
        </div>

        <p style={{ fontSize: "0.86rem", color: "var(--ink-secondary)", lineHeight: 1.6, marginTop: 10 }}>
          {selectedAgent.deepDetails}
        </p>

        <div className="spec-grid">
          <div className="spec-item">
            <div className="spec-item-label">Tech Stack & Components</div>
            <div className="spec-item-val" style={{ fontFamily: "var(--mono)" }}>{selectedAgent.techStack}</div>
          </div>
          <div className="spec-item">
            <div className="spec-item-label">Resilience & Failure Isolation</div>
            <div className="spec-item-val">{selectedAgent.resilience}</div>
          </div>
          <div className="spec-item">
            <div className="spec-item-label">State Machine Role</div>
            <div className="spec-item-val">{selectedAgent.oneLiner}</div>
          </div>
        </div>
      </div>
    </section>
  );
}
