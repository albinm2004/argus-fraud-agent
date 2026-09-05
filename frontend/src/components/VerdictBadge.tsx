const STATUS = {
  block: { color: "var(--status-block)", bg: "var(--status-block-bg)", label: "BLOCK" },
  flag: { color: "var(--status-flag)", bg: "var(--status-flag-bg)", label: "FLAG" },
  allow: { color: "var(--status-allow)", bg: "var(--status-allow-bg)", label: "ALLOW" },
} as const;

export function VerdictBadge({ verdict }: { verdict: "block" | "flag" | "allow" }) {
  const s = STATUS[verdict] ?? STATUS.allow;
  return (
    <span className="verdict-badge" style={{ background: s.bg, color: s.color }}>
      <span className="verdict-dot" style={{ background: s.color }} />
      {s.label}
    </span>
  );
}
