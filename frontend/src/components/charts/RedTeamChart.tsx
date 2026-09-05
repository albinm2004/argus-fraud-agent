/* The adversarial attack, per transaction, instead of as one summary number.

   Each row is one of the borderline transactions the red-team agent attacked:
   the dot on the left is the score before the attack, the dot on the right is
   the score after the attacker nudged amount/velocity features, and the
   connector is how far they moved it. The threshold line is what matters --
   an attack only "succeeds" if it drags a fraud transaction across it.

   Two series, so a legend is present; the connector is a recessive hairline
   so the dots, not the line, carry the reading. */
import { useState } from "react";
import type { Transaction } from "../../types";

const W = 720;
const ROW_H = 22;
const M = { top: 34, right: 58, bottom: 46, left: 82 };

export function RedTeamChart({ transactions }: { transactions: Transaction[] }) {
  const [hover, setHover] = useState<number | null>(null);

  const rows = transactions
    .filter((t) => t.red_team !== null)
    .sort((a, b) => b.red_team!.pre - a.red_team!.pre);

  if (rows.length === 0) return null;

  const threshold = rows[0].threshold;
  const plotW = W - M.left - M.right;
  const H = M.top + rows.length * ROW_H + M.bottom;

  const lo = Math.max(0, Math.min(...rows.flatMap((r) => [r.red_team!.pre, r.red_team!.post])) - 0.05);
  const hi = Math.min(1, Math.max(...rows.flatMap((r) => [r.red_team!.pre, r.red_team!.post])) + 0.05);
  const x = (v: number) => M.left + ((v - lo) / (hi - lo)) * plotW;

  const anyEvaded = rows.some((r) => r.red_team!.evaded);

  const tickStep = hi - lo > 0.4 ? 0.1 : 0.05;
  const ticks: number[] = [];
  for (let v = Math.ceil(lo / tickStep) * tickStep; v <= hi + 1e-9; v += tickStep) {
    ticks.push(Math.round(v * 100) / 100);
  }

  return (
    <div className="chart-card">
      <div className="chart-head">
        <div>
          <h3 className="chart-title">Attack trajectories on the {rows.length} most borderline cases</h3>
          <p className="chart-sub">
            The red-team agent perturbs each transaction&apos;s own amount and velocity features to
            push its score down. An attack only succeeds if it crosses the threshold.
          </p>
        </div>
        <div className="legend-row">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "var(--series-1)" }} />
            Before attack
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "var(--series-2)" }} />
            After attack
          </span>
        </div>
      </div>

      <div className="chart-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img">
          {/* threshold band -- everything left of the line is an evasion */}
          {x(threshold) > M.left && (
            <rect
              x={M.left}
              y={M.top - 8}
              width={Math.max(0, x(threshold) - M.left)}
              height={rows.length * ROW_H + 10}
              fill="var(--status-block)"
              opacity="0.06"
            />
          )}
          <line
            x1={x(threshold)}
            x2={x(threshold)}
            y1={M.top - 10}
            y2={M.top + rows.length * ROW_H}
            stroke="var(--ink-secondary)"
            strokeWidth="2"
            strokeDasharray="4 3"
          />
          <text x={x(threshold)} y={M.top - 16} textAnchor="middle" className="axis-label strong">
            threshold {threshold.toFixed(3)}
          </text>

          {rows.map((t, i) => {
            const rt = t.red_team!;
            const y = M.top + i * ROW_H + ROW_H / 2;
            const active = hover === t.id;
            return (
              <g
                key={t.id}
                onMouseEnter={() => setHover(t.id)}
                onMouseLeave={() => setHover(null)}
              >
                <rect x={0} y={y - ROW_H / 2} width={W} height={ROW_H} fill="transparent" />
                <text x={M.left - 12} y={y + 4} textAnchor="end" className="row-label">
                  {t.id}
                </text>
                <line
                  x1={x(rt.pre)}
                  x2={x(rt.post)}
                  y1={y}
                  y2={y}
                  stroke={active ? "var(--ink-secondary)" : "var(--axis)"}
                  strokeWidth="2"
                />
                <circle cx={x(rt.pre)} cy={y} r="5" fill="var(--series-1)" />
                <circle cx={x(rt.post)} cy={y} r="5" fill="var(--series-2)" />
                <text x={W - M.right + 10} y={y + 4} className="axis-label">
                  {rt.post.toFixed(3)}
                </text>
              </g>
            );
          })}

          <line
            x1={M.left}
            x2={W - M.right}
            y1={M.top + rows.length * ROW_H + 2}
            y2={M.top + rows.length * ROW_H + 2}
            stroke="var(--axis)"
            strokeWidth="1"
          />
          {ticks.map((v) => (
            <text key={v} x={x(v)} y={M.top + rows.length * ROW_H + 17} textAnchor="middle" className="axis-label">
              {v.toFixed(2)}
            </text>
          ))}
          <text
            x={M.left + plotW / 2}
            y={H - 6}
            textAnchor="middle"
            className="axis-title"
          >
            model score &mdash; {anyEvaded
              ? "some attacks crossed the threshold"
              : "no attack crossed the threshold; the hardened model held on every case"}
          </text>
        </svg>
      </div>
    </div>
  );
}
