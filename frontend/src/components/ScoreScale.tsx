const STATUS_COLOR = {
  block: "var(--status-block)",
  flag: "var(--status-flag)",
  allow: "var(--status-allow)",
} as const;

export function ScoreScale({
  score,
  threshold,
  verdict,
}: {
  score: number;
  threshold: number;
  verdict: "block" | "flag" | "allow";
}) {
  const color = STATUS_COLOR[verdict] ?? STATUS_COLOR.allow;
  const scorePct = Math.max(0, Math.min(1, score)) * 100;
  const threshPct = Math.max(0, Math.min(1, threshold)) * 100;
  return (
    <div>
      <div className="score-scale">
        <div className="track" />
        <div className="fill" style={{ width: `${scorePct}%`, background: color }} />
        <div
          className="threshold-tick"
          style={{ left: `${threshPct}%` }}
          title={`Decision threshold ${threshold.toFixed(3)}`}
        />
        <div className="marker" style={{ left: `${scorePct}%`, background: color }} />
      </div>
      <div className="score-scale-labels">
        <span>0.0</span>
        <span>
          score {score.toFixed(3)} · threshold {threshold.toFixed(3)}
        </span>
        <span>1.0</span>
      </div>
    </div>
  );
}
