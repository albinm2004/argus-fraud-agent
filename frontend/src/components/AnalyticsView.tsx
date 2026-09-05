import type { Transaction } from "../types";
import { ScoreDistribution } from "./charts/ScoreDistribution";
import { EvidenceDrivers } from "./charts/EvidenceDrivers";

export function AnalyticsView({ transactions }: { transactions: Transaction[] }) {
  /* graph.source says WHICH graph answered; graph.found says whether that
     graph actually held a record for the transaction. They're independent --
     a live Neo4j lookup that legitimately finds nothing is source "neo4j"
     with found false -- so these are counted separately, never subtracted
     from each other. */
  const liveGraph = transactions.filter((t) => t.graph.source === "neo4j").length;
  const fallbackGraph = transactions.filter(
    (t) => t.graph.source && t.graph.source !== "neo4j",
  ).length;
  const withRecord = transactions.filter((t) => t.graph.found).length;
  const linked = transactions.filter(
    (t) => (t.graph.shared_card_count ?? 0) > 0 || (t.graph.shared_addr_count ?? 0) > 0,
  ).length;

  return (
    <>
      <ScoreDistribution transactions={transactions} />
      <EvidenceDrivers transactions={transactions} />

      <div className="chart-card">
        <h3 className="chart-title">Graph coverage</h3>
        <p className="chart-sub">
          Where the entity-graph signal in each evidence chain came from, across the sample.
        </p>
        <div className="coverage-row">
          <div className="coverage-item">
            <span className="coverage-value">{liveGraph}</span>
            <span className="coverage-label">
              answered by live Neo4j{fallbackGraph > 0 ? ` (${fallbackGraph} by local fallback)` : ""}
            </span>
          </div>
          <div className="coverage-item">
            <span className="coverage-value">{withRecord}</span>
            <span className="coverage-label">had a record in the graph</span>
          </div>
          <div className="coverage-item">
            <span className="coverage-value">{linked}</span>
            <span className="coverage-label">linked to another transaction</span>
          </div>
          <div className="coverage-item">
            <span className="coverage-value">{transactions.length - withRecord}</span>
            <span className="coverage-label">no record yet &mdash; first sighting</span>
          </div>
        </div>
      </div>
    </>
  );
}
