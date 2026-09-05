import { useMemo, useState } from "react";
import { useDashboardData } from "./data/useDashboardData";
import { HeroMetrics } from "./components/HeroMetrics";
import { TransactionFeed } from "./components/TransactionFeed";
import { EvidencePanel } from "./components/EvidencePanel";
import { ArchitectureView } from "./components/ArchitectureView";
import { RobustnessPanel } from "./components/RobustnessPanel";

type Tab = "overview" | "architecture" | "robustness";

export default function App() {
  const { data, loading, error } = useDashboardData();
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selected = useMemo(
    () => data?.transactions.find((t) => t.id === selectedId) ?? null,
    [data, selectedId],
  );

  return (
    <div className="argus-app">
      <div className="argus-hero">
        <div className="shield">🛡️</div>
        <div>
          <p className="title">Argus</p>
          <p className="tagline">
            Multi-agent fraud investigation &mdash; Razorpay AI Buildathon, Track 2 (AI Risk
            Manager)
          </p>
        </div>
        {data && (
          <div className="meta">
            {data.n_sample} transactions &middot; generated {new Date(data.generated_at).toLocaleString()}
          </div>
        )}
      </div>

      {loading && <div className="state-msg">Loading pipeline output&hellip;</div>}
      {error && (
        <div className="state-msg">
          Couldn&apos;t load dashboard.json ({error}). Run{" "}
          <code>python scripts/export_dashboard_data.py</code> from the repo root first.
        </div>
      )}

      {data && (
        <>
          <div className="argus-tabs">
            <button
              className={`argus-tab ${tab === "overview" ? "active" : ""}`}
              onClick={() => setTab("overview")}
            >
              Overview
            </button>
            <button
              className={`argus-tab ${tab === "architecture" ? "active" : ""}`}
              onClick={() => setTab("architecture")}
            >
              Architecture
            </button>
            <button
              className={`argus-tab ${tab === "robustness" ? "active" : ""}`}
              onClick={() => setTab("robustness")}
            >
              Adversarial robustness
            </button>
          </div>

          {tab === "overview" && (
            <>
              {data.metrics && <HeroMetrics metrics={data.metrics} />}
              <div className="split-view">
                <TransactionFeed
                  transactions={data.transactions}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
                <EvidencePanel txn={selected} />
              </div>
            </>
          )}

          {tab === "architecture" && <ArchitectureView />}

          {tab === "robustness" && data.metrics && <RobustnessPanel metrics={data.metrics} />}
        </>
      )}

      <div className="argus-footer">
        Argus &mdash; built for the Razorpay AI Buildathon. Every number above comes from the real
        pipeline (agents/verdict.py, agents/graph_builder.py, agents/red_team.py), precomputed via
        scripts/export_dashboard_data.py rather than served live &mdash; see the project README for
        why. Known limitations tracked honestly there too.
      </div>
    </div>
  );
}
