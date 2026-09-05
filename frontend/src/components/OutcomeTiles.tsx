/* The four outcomes, counted from the sample -- a confusion matrix without
   making a judge parse a confusion matrix.

   Status color here is legitimate (these ARE outcome states, not series), and
   every tile carries its own label and count, so the color never has to carry
   the meaning alone. */
import type { Transaction } from "../types";

interface Outcome {
  key: string;
  label: string;
  hint: string;
  count: number;
  tone: "good" | "critical" | "warning" | "neutral";
}

export function OutcomeTiles({ transactions }: { transactions: Transaction[] }) {
  const flagged = (t: Transaction) => t.verdict_bucket === "flag/block";

  const caught = transactions.filter((t) => t.actual === "fraud" && flagged(t)).length;
  const missed = transactions.filter((t) => t.actual === "fraud" && !flagged(t)).length;
  const falseAlarm = transactions.filter((t) => t.actual === "legit" && flagged(t)).length;
  const cleared = transactions.filter((t) => t.actual === "legit" && !flagged(t)).length;

  const outcomes: Outcome[] = [
    { key: "caught", label: "Fraud caught", hint: "flagged or blocked, actually fraud", count: caught, tone: "good" },
    { key: "missed", label: "Fraud missed", hint: "allowed through, actually fraud", count: missed, tone: "critical" },
    { key: "false", label: "False alarms", hint: "flagged, actually legitimate", count: falseAlarm, tone: "warning" },
    { key: "cleared", label: "Correctly cleared", hint: "allowed through, actually legitimate", count: cleared, tone: "neutral" },
  ];

  return (
    <div className="outcome-grid">
      {outcomes.map((o) => (
        <div key={o.key} className={`outcome-tile tone-${o.tone}`}>
          <div className="outcome-count">{o.count}</div>
          <div className="outcome-label">{o.label}</div>
          <div className="outcome-hint">{o.hint}</div>
        </div>
      ))}
    </div>
  );
}
