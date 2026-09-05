/* Score distribution -- how separable the two classes actually are.

   The single most honest chart in this app: it shows the model's score for
   every held-out transaction, split by what the transaction actually was,
   with the decision threshold drawn where it really sits. Overlap between
   the two series IS the error rate -- the recall number in the tiles above
   is this picture, counted.

   Colors are categorical (identity: fraud vs legit), NOT status -- status
   red/amber/green stays reserved for verdict state elsewhere in the app.
   Palette slots 1 and 2 of the validated dark ramp; validated all-pairs
   against this app's own surface. */
import { useState } from "react";
import type { Transaction } from "../../types";

const W = 720;
const H = 252;
const M = { top: 14, right: 14, bottom: 34, left: 46 };
const N_BINS = 20;

interface Bin {
  x0: number;
  x1: number;
  fraud: number;
  legit: number;
}

export function ScoreDistribution({ transactions }: { transactions: Transaction[] }) {
  const [hover, setHover] = useState<{ bin: Bin; x: number; y: number } | null>(null);

  const bins: Bin[] = Array.from({ length: N_BINS }, (_, i) => ({
    x0: i / N_BINS,
    x1: (i + 1) / N_BINS,
    fraud: 0,
    legit: 0,
  }));

  for (const t of transactions) {
    const idx = Math.min(N_BINS - 1, Math.floor(t.score * N_BINS));
    if (t.actual === "fraud") bins[idx].fraud += 1;
    else bins[idx].legit += 1;
  }

  const maxCount = Math.max(1, ...bins.map((b) => Math.max(b.fraud, b.legit)));
  const threshold = transactions[0]?.threshold ?? 0.5;

  const plotW = W - M.left - M.right;
  const plotH = H - M.top - M.bottom;
  const xScale = (v: number) => M.left + v * plotW;
  const yScale = (c: number) => M.top + plotH - (c / maxCount) * plotH;

  const groupW = plotW / N_BINS;
  const barW = Math.max(2, (groupW - 4) / 2);

  const yTicks = [0, Math.round(maxCount / 2), maxCount].filter(
    (v, i, a) => a.indexOf(v) === i,
  );

  return (
    <div className="chart-card">
      <div className="chart-head">
        <div>
          <h3 className="chart-title">Score distribution by actual outcome</h3>
          <p className="chart-sub">
            Every held-out transaction in the sample, binned by the score the model gave it. The
            gap between the two series is the signal; the overlap is the error.
          </p>
        </div>
        <div className="legend-row">
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: "var(--series-1)" }} />
            Actually legit
          </span>
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: "var(--series-2)" }} />
            Actually fraud
          </span>
        </div>
      </div>

      <div className="chart-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" role="img">
          {/* gridlines + y axis */}
          {yTicks.map((t) => (
            <g key={t}>
              <line
                x1={M.left}
                x2={W - M.right}
                y1={yScale(t)}
                y2={yScale(t)}
                stroke="var(--grid)"
                strokeWidth="1"
              />
              <text x={M.left - 10} y={yScale(t) + 4} textAnchor="end" className="axis-label">
                {t}
              </text>
            </g>
          ))}

          {/* bars */}
          {bins.map((b, i) => {
            const gx = xScale(b.x0) + 2;
            return (
              <g
                key={i}
                onMouseEnter={() => setHover({ bin: b, x: gx + groupW / 2, y: M.top })}
                onMouseLeave={() => setHover(null)}
              >
                <rect
                  x={xScale(b.x0)}
                  y={M.top}
                  width={groupW}
                  height={plotH}
                  fill="transparent"
                />
                {b.legit > 0 && (
                  <rect
                    x={gx}
                    y={yScale(b.legit)}
                    width={barW}
                    height={M.top + plotH - yScale(b.legit)}
                    rx="3"
                    fill="var(--series-1)"
                  />
                )}
                {b.fraud > 0 && (
                  <rect
                    x={gx + barW + 2}
                    y={yScale(b.fraud)}
                    width={barW}
                    height={M.top + plotH - yScale(b.fraud)}
                    rx="3"
                    fill="var(--series-2)"
                  />
                )}
              </g>
            );
          })}

          {/* baseline */}
          <line
            x1={M.left}
            x2={W - M.right}
            y1={M.top + plotH}
            y2={M.top + plotH}
            stroke="var(--axis)"
            strokeWidth="1"
          />

          {/* threshold */}
          <line
            x1={xScale(threshold)}
            x2={xScale(threshold)}
            y1={M.top - 2}
            y2={M.top + plotH}
            stroke="var(--ink-secondary)"
            strokeWidth="2"
            strokeDasharray="4 3"
          />
          <text
            x={xScale(threshold) - 8}
            y={M.top + 10}
            textAnchor="end"
            className="axis-label strong"
          >
            threshold {threshold.toFixed(3)}
          </text>

          {/* x ticks */}
          {[0, 0.25, 0.5, 0.75, 1].map((v) => (
            <text
              key={v}
              x={xScale(v)}
              y={H - 12}
              textAnchor="middle"
              className="axis-label"
            >
              {v.toFixed(2)}
            </text>
          ))}
          <text x={M.left + plotW / 2} y={H - 0.5} textAnchor="middle" className="axis-title">
            model score
          </text>
        </svg>

        {hover && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(hover.x / W) * 100}%`,
              top: 6,
            }}
          >
            <div className="tt-head">
              score {hover.bin.x0.toFixed(2)}&ndash;{hover.bin.x1.toFixed(2)}
            </div>
            <div className="tt-row">
              <span className="legend-swatch" style={{ background: "var(--series-2)" }} />
              {hover.bin.fraud} fraud
            </div>
            <div className="tt-row">
              <span className="legend-swatch" style={{ background: "var(--series-1)" }} />
              {hover.bin.legit} legit
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
