import { useMemo, useState } from "react";
import type { Transaction } from "../types";

type Filter = "all" | "flag/block" | "allow";

export function TransactionFeed({
  transactions,
  selectedId,
  onSelect,
}: {
  transactions: Transaction[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");

  const rows = useMemo(() => {
    const filtered =
      filter === "all" ? transactions : transactions.filter((t) => t.verdict_bucket === filter);
    return [...filtered].sort((a, b) => b.score - a.score);
  }, [transactions, filter]);

  return (
    <div className="panel">
      <h2>Transaction feed (held-out, sampled)</h2>
      <div className="filter-row">
        {(["all", "flag/block", "allow"] as Filter[]).map((f) => (
          <button
            key={f}
            className={`filter-pill ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>
      <div className="feed-table-wrap">
        <table className="feed-table">
          <thead>
            <tr>
              <th>TransactionID</th>
              <th style={{ textAlign: "right" }}>Amount</th>
              <th style={{ textAlign: "right" }}>Score</th>
              <th>Verdict</th>
              <th>Actual</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const flagged = t.verdict_bucket === "flag/block";
              const isMiss = (t.actual === "fraud") !== flagged;
              return (
                <tr
                  key={t.id}
                  className={t.id === selectedId ? "selected" : ""}
                  onClick={() => onSelect(t.id)}
                >
                  <td>{t.id}</td>
                  <td className="num">{t.amount.toFixed(2)}</td>
                  <td className="num">{t.score.toFixed(3)}</td>
                  <td>
                    <span
                      className="verdict-cell"
                      style={{ color: flagged ? "var(--status-block)" : "var(--status-allow)" }}
                    >
                      {t.verdict_bucket}
                    </span>
                    {isMiss && <span className="miss-flag">MISS</span>}
                  </td>
                  <td>{t.actual}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
