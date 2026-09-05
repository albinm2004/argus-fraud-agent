/* Which features actually drive decisions, across the whole sample.

   Counts how often each feature shows up in a transaction's evidence chain,
   split by which way it pushed the score. Diverging form (raised right /
   lowered left, neutral center) because the quantity being encoded is signed
   -- the same semantics, and the same blue/red pair, as the per-transaction
   evidence bars in the investigation panel, so a judge who learned to read
   those reads this one for free. */
import { useState } from "react";
import type { Transaction } from "../../types";

const W = 720;
const ROW_H = 26;
const M = { top: 30, right: 46, bottom: 26, left: 96 };
const TOP_N = 9;

interface Driver {
  feature: string;
  raised: number;
  lowered: number;
  total: number;
}

/* Evidence lines read like "velocity/count signal C1 = 10.0 (...) -- raised
   risk score by 1.442". The feature name is the identifier immediately before
   the "=", which is stable across every line shape the verdict renderer emits. */
function featureOf(text: string): string | null {
  const m = text.match(/([A-Za-z0-9_]+)\s*=/);
  return m ? m[1] : null;
}

export function EvidenceDrivers({ transactions }: { transactions: Transaction[] }) {
  const [hover, setHover] = useState<Driver | null>(null);

  const byFeature = new Map<string, Driver>();
  for (const t of transactions) {
    for (const line of t.evidence) {
      if (!line.direction) continue;
      const f = featureOf(line.text);
      if (!f) continue;
      const d = byFeature.get(f) ?? { feature: f, raised: 0, lowered: 0, total: 0 };
      if (line.direction === "raised") d.raised += 1;
      else d.lowered += 1;
      d.total += 1;
      byFeature.set(f, d);
    }
  }

  const drivers = [...byFeature.values()].sort((a, b) => b.total - a.total).slice(0, TOP_N);
  if (drivers.length === 0) return null;

  const maxSide = Math.max(1, ...drivers.map((d) => Math.max(d.raised, d.lowered)));
  const plotW = W - M.left - M.right;
  const mid = M.left + plotW / 2;
  const halfW = plotW / 2;
  const H = M.top + drivers.length * ROW_H + M.bottom;
  const scale = (n: number) => (n / maxSide) * (halfW - 8);

  return (
    <div className="chart-card">
      <div className="chart-head">
        <div>
          <h3 className="chart-title">What the model actually keys on</h3>
          <p className="chart-sub">
            How often each feature appeared in an evidence chain across all {transactions.length}{" "}
            transactions, and which way it pushed the score.
          </p>
        </div>
        <div className="legend-row">
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: "var(--diverge-down)" }} />
            Lowered risk
          </span>
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: "var(--diverge-up)" }} />
            Raised risk
          </span>
        </div>
      </div>

      <div className="chart-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img">
          <text x={mid - 10} y={16} textAnchor="end" className="axis-label">
            &larr; lowered
          </text>
          <text x={mid + 10} y={16} textAnchor="start" className="axis-label">
            raised &rarr;
          </text>

          {drivers.map((d, i) => {
            const y = M.top + i * ROW_H;
            const barY = y + 5;
            const barH = ROW_H - 12;
            return (
              <g
                key={d.feature}
                onMouseEnter={() => setHover(d)}
                onMouseLeave={() => setHover(null)}
              >
                <rect x={0} y={y} width={W} height={ROW_H} fill="transparent" />
                <text x={M.left - 12} y={y + ROW_H / 2 + 4} textAnchor="end" className="row-label">
                  {d.feature}
                </text>
                {d.lowered > 0 && (
                  <rect
                    x={mid - 1 - scale(d.lowered)}
                    y={barY}
                    width={scale(d.lowered)}
                    height={barH}
                    rx="3"
                    fill="var(--diverge-down)"
                  />
                )}
                {d.raised > 0 && (
                  <rect
                    x={mid + 1}
                    y={barY}
                    width={scale(d.raised)}
                    height={barH}
                    rx="3"
                    fill="var(--diverge-up)"
                  />
                )}
                <text x={W - 4} y={y + ROW_H / 2 + 4} textAnchor="end" className="axis-label">
                  {d.total}
                </text>
              </g>
            );
          })}

          <line
            x1={mid}
            x2={mid}
            y1={M.top - 6}
            y2={M.top + drivers.length * ROW_H + 2}
            stroke="var(--axis)"
            strokeWidth="1"
          />
        </svg>

        {hover && (
          <div className="chart-tooltip static-tt">
            <div className="tt-head">{hover.feature}</div>
            <div className="tt-row">
              <span className="legend-swatch" style={{ background: "var(--diverge-up)" }} />
              raised risk in {hover.raised} transactions
            </div>
            <div className="tt-row">
              <span className="legend-swatch" style={{ background: "var(--diverge-down)" }} />
              lowered risk in {hover.lowered} transactions
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
