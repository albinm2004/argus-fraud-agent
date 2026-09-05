const AGENTS = [
  {
    name: "Watcher",
    desc: "Verifies the Razorpay webhook's HMAC-SHA256 signature and normalizes the event -- rejects anything tampered before it reaches the rest of the pipeline.",
  },
  {
    name: "Graph Builder",
    desc: "Checks the transaction against a live Neo4j entity graph (shared card / address rings), falling back to a local graph if Neo4j is unreachable -- the pipeline never goes dark over one dependency.",
  },
  {
    name: "Pattern Analyst",
    desc: "Scores the transaction with a hardened XGBoost model trained on graph-aware features, time-split to avoid leakage from the future into training.",
  },
  {
    name: "Red-Team",
    desc: "Adversarially perturbs the transaction's own amount/velocity features to test whether a fraudster could evade the score -- reports a measured robustness delta, not an assumed one.",
  },
  {
    name: "Verdict + Audit",
    desc: "Renders block / flag / allow with a real per-feature SHAP evidence chain and logs the decision to a rotating audit trail -- every call is explainable, not just scored.",
  },
] as const;

export function ArchitectureView() {
  return (
    <div className="panel">
      <h2>Five agents, one audit trail</h2>
      <p style={{ color: "var(--ink-secondary)", fontSize: "0.88rem", marginTop: -6 }}>
        Wired as a real LangGraph state machine, not functions called in sequence. Hover a stage
        for what it actually does.
      </p>
      <div className="arch-flow">
        {AGENTS.map((a, i) => (
          <div key={a.name} style={{ display: "flex", alignItems: "stretch", flex: 1 }}>
            <div className="arch-node">
              <div className="n">STAGE {i + 1}</div>
              <div className="name">{a.name}</div>
              <div className="desc">{a.desc}</div>
            </div>
            {i < AGENTS.length - 1 && <div className="arch-arrow-wrap">→</div>}
          </div>
        ))}
      </div>
      <h3>Why this shape</h3>
      <p style={{ color: "var(--ink-secondary)", fontSize: "0.86rem", lineHeight: 1.6 }}>
        Most fraud demos stop at a score. Argus treats every transaction like a case file: the
        graph stage answers &ldquo;who else is this connected to,&rdquo; the red-team stage
        answers &ldquo;could this be gamed,&rdquo; and the verdict stage answers &ldquo;why&rdquo;
        &mdash; in plain language, not just a number. Full diagram: docs/architecture.md.
      </p>
    </div>
  );
}
