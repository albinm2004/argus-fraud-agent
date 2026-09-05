import type { Transaction } from "../types";
import { VerdictBadge } from "./VerdictBadge";
import { ScoreScale } from "./ScoreScale";
import { EvidenceBar } from "./EvidenceBar";

function PipelineStrip({ ranRedTeam }: { ranRedTeam: boolean }) {
  const nodes = [
    { name: "Watcher", active: true },
    { name: "Graph Builder", active: true },
    { name: "Pattern Analyst", active: true },
    { name: ranRedTeam ? "Red-Team" : "Red-Team (skipped)", active: ranRedTeam },
    { name: "Verdict", active: true },
  ];
  return (
    <div className="pipeline-strip">
      {nodes.map((n, i) => (
        <span key={n.name}>
          <span className={`pipeline-node ${n.active ? "active" : ""}`}>{n.name}</span>
          {i < nodes.length - 1 && <span className="pipeline-arrow"> → </span>}
        </span>
      ))}
    </div>
  );
}

function GraphChips({ graph }: { graph: Transaction["graph"] }) {
  if (!graph.found) {
    return <div className="evidence-legend">Transaction not found in the loaded graph.</div>;
  }
  const fraudCount = graph.other_fraud_in_component ?? graph.neighbor_fraud_count;
  return (
    <div className="chip-row">
      <span className="chip">
        Source: <b>{graph.source ?? "unknown"}</b>
      </span>
      <span className="chip">
        Shared card: <b>{graph.shared_card_count ?? 0}</b>
      </span>
      <span className="chip">
        Shared address: <b>{graph.shared_addr_count ?? 0}</b>
      </span>
      {fraudCount !== undefined && (
        <span className="chip">
          Fraud nearby: <b>{fraudCount}</b>
        </span>
      )}
    </div>
  );
}

function RedTeamCallout({ redTeam }: { redTeam: Transaction["red_team"] }) {
  if (!redTeam) {
    return (
      <div className="evidence-legend">
        Robustness check not computed for this transaction (pinned to the 15 most
        borderline cases -- see scripts/export_dashboard_data.py).
      </div>
    );
  }
  return (
    <div className="chip-row">
      <span className="chip">
        Pre-attack score: <b>{redTeam.pre.toFixed(3)}</b>
      </span>
      <span className="chip">
        Post-attack score: <b>{redTeam.post.toFixed(3)}</b>
      </span>
      <span className="chip" style={{ color: redTeam.evaded ? "var(--status-block)" : "var(--status-allow)" }}>
        {redTeam.evaded ? "Evaded" : "Held"}
      </span>
    </div>
  );
}

export function EvidencePanel({ txn }: { txn: Transaction | null }) {
  if (!txn) {
    return (
      <div className="panel">
        <h2>Evidence chain</h2>
        <div className="state-msg">Select a transaction from the feed.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Evidence chain</h2>
      <VerdictBadge verdict={txn.verdict} />
      <div style={{ color: "var(--ink-secondary)", fontSize: "0.82rem", marginTop: 8 }}>
        Ground truth: {txn.actual === "fraud" ? "FRAUD" : "legit"} &middot; txn {txn.id}
      </div>
      <ScoreScale score={txn.score} threshold={txn.threshold} verdict={txn.verdict} />
      <PipelineStrip ranRedTeam={txn.red_team !== null} />

      <h3>Why</h3>
      {txn.evidence.map((line, i) => (
        <EvidenceBar key={i} line={line} />
      ))}
      <div className="evidence-legend">
        Red bars raised the risk score, blue bars lowered it &mdash; bar length is the magnitude
        of that feature&apos;s SHAP contribution (XGBoost native <code>pred_contribs</code>, not
        the <code>shap</code> package).
      </div>

      <h3>Graph signal</h3>
      <GraphChips graph={txn.graph} />

      <h3>Adversarial robustness</h3>
      <RedTeamCallout redTeam={txn.red_team} />
    </div>
  );
}
