import type { EvidenceLine } from "../types";

// Strip this fixed caveat out of the displayed text -- it's boilerplate
// baked into every C-signal's precomputed description (Kaggle obfuscates
// those columns), not something worth spelling out on every single line.
const CAVEAT = " (Kaggle doesn't disclose exact semantics \u2014 treated as a general velocity signal)";

export function EvidenceBar({ line }: { line: EvidenceLine }) {
  const text = line.text.replace(CAVEAT, "");
  if (!line.direction || line.magnitude === null) {
    return (
      <div className="evidence-row">
        <div className="evidence-text">{text}</div>
      </div>
    );
  }
  const pct = Math.min(48, line.magnitude * 60);
  const color = line.direction === "raised" ? "var(--diverge-up)" : "var(--diverge-down)";
  const left = line.direction === "raised" ? 50 : 50 - pct;
  return (
    <div className="evidence-row">
      <div className="evidence-text">{text}</div>
      <div className="evidence-bar-track">
        <div className="evidence-bar-center" />
        <div
          className="evidence-bar-fill"
          style={{ left: `${left}%`, width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}
