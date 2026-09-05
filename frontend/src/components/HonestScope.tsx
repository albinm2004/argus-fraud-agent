export function HonestScope() {
  const CHOICES = [
    {
      tag: "Design Decision 1",
      title: "Precomputed Benchmark, Not a Live API",
      body:
        "Every transaction, SHAP evidence chain, graph count, and adversarial trajectory in this dashboard was precomputed by the real ML pipeline (agents/verdict.py, agents/graph_builder.py, agents/red_team.py) and exported via scripts/export_dashboard_data.py. We chose a static artifact for this showcase frontend so pitch reviewers and judges experience sub-millisecond response times without depending on live cloud database connectivity.",
    },
    {
      tag: "Design Decision 2",
      title: "IEEE-CIS Dataset with Razorpay Contracts",
      body:
        "The model is trained on the IEEE-CIS benchmark (590K transactions, 3.5% real-world fraud base rate) and adapted to Razorpay webhook payload contracts. It is not trained on private Razorpay merchant transactions. This ensures full reproducibility and legal auditability without compromising confidential cardholder data.",
    },
    {
      tag: "Design Decision 3",
      title: "Scoped Adversarial Attack Family",
      body:
        "Our 0.0% hardened evasion rate is proven against a black-box perturbation family (±35% amount and velocity jitter). While this demonstrates that adversarial training closes the feature-nudging vulnerability, it is not an unbounded claim of invulnerability against entirely novel attack vectors. In production, continuous adversarial retraining would be maintained.",
    },
    {
      tag: "Design Decision 4",
      title: "Time-Based Split (Strictly No Leakage)",
      body:
        "We reject random train/test shuffling. In financial fraud, shuffling leaks future fraud patterns into past training windows. All 300 test transactions and the 1,500 attack sample cases come strictly from held-out future timestamps, which is why our 46.9% recall and 91% ROC-AUC numbers are unpadded and reflect real operational conditions.",
    },
  ];

  return (
    <section className="story-section" id="scope">
      <div className="section-header">
        <div className="section-eyebrow">
          <span>Engineering Transparency</span>
          <span>&middot;</span>
          <span>What This Is and Isn&apos;t</span>
        </div>
        <h2 className="section-title">Deliberate design choices, stated plainly</h2>
        <p className="section-desc">
          We treat transparent boundaries as a hallmark of professional systems engineering, not a
          disclaimer buried in fine print. Here is the exact scope and operational context of Argus.
        </p>
      </div>

      <div className="scope-cards-grid">
        {CHOICES.map((item, idx) => (
          <div key={idx} className="scope-card">
            <span className="scope-card-tag">{item.tag}</span>
            <div className="scope-card-title">{item.title}</div>
            <p className="scope-card-body">{item.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
