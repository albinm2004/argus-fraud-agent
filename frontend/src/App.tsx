import { useState, useMemo } from "react";
import { useDashboardData } from "./data/useDashboardData";
import { LogoLockup } from "./components/Logo";
import { HeroHook } from "./components/HeroHook";
import { FeaturedWalkthrough } from "./components/FeaturedWalkthrough";
import { AggregateProof } from "./components/AggregateProof";
import { AdversarialClimax } from "./components/AdversarialClimax";
import { ArchitecturePipeline } from "./components/ArchitecturePipeline";
import { HonestScope } from "./components/HonestScope";

export default function App() {
  const { data, loading, error } = useDashboardData();

  // Default featured transaction: 3464462 (Dramatic 82% fraud cluster case)
  const [selectedId, setSelectedId] = useState<number>(3464462);

  const selectedTxn = useMemo(() => {
    if (!data || !data.transactions.length) return null;
    return data.transactions.find((t) => t.id === selectedId) ?? data.transactions[0];
  }, [data, selectedId]);

  // Picking a transaction from anywhere on the page (the 300-row feed, an
  // archetype pill, etc.) should jump back up to the walkthrough so the
  // updated step-by-step story is immediately visible, not just updated
  // off-screen above wherever the visitor happens to be scrolled to.
  const handleSelectTxn = (id: number) => {
    setSelectedId(id);
    const el = document.getElementById("walkthrough");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="showcase-root">
      {/* Sticky Top Navigation Bar */}
      <header className="top-navbar">
        <div className="nav-brand-group">
          <LogoLockup />
        </div>

        <nav className="nav-links">
          <a href="#hook" className="nav-link-btn">
            Hook
          </a>
          <a href="#walkthrough" className="nav-link-btn">
            Proof by Example
          </a>
          <a href="#metrics" className="nav-link-btn">
            Aggregate Proof
          </a>
          <a href="#adversarial" className="nav-link-btn">
            Adversarial Climax
          </a>
          <a href="#architecture" className="nav-link-btn">
            5-Agent Architecture
          </a>
          <a href="#scope" className="nav-link-btn">
            Engineering Scope
          </a>
        </nav>

        <div className="topbar-meta-badge">
          <span className="pulse-dot" />
          <span>300 Real Transactions Scored</span>
        </div>
      </header>

      {/* Main Narrative Container */}
      <main className="main-container">
        {loading && (
          <div className="state-msg">
            <div className="pulse-dot" style={{ display: "inline-block", marginRight: 8 }} />
            Loading real pipeline outputs from <code>dashboard.json</code>&hellip;
          </div>
        )}

        {error && (
          <div className="state-msg" style={{ color: "var(--status-block)" }}>
            Error loading pipeline dataset ({error}). Ensure <code>frontend/public/data/dashboard.json</code> exists.
          </div>
        )}

        {data && selectedTxn && (
          <>
            {/* 1. Above-the-fold Hook */}
            <HeroHook
              featuredTxn={selectedTxn}
              onSelectTxn={handleSelectTxn}
            />

            {/* 2. Proof by Example (Featured Walkthrough + Expandable Feed) */}
            <FeaturedWalkthrough
              transactions={data.transactions}
              selectedTxn={selectedTxn}
              onSelectTxn={handleSelectTxn}
            />

            {/* 3. Aggregate Proof (Metrics with Plain-Language Consequences) */}
            {data.metrics && (
              <AggregateProof
                metrics={data.metrics}
                transactions={data.transactions}
              />
            )}

            {/* 4. Adversarial Climax (The Differentiator) */}
            {data.metrics && (
              <AdversarialClimax
                metrics={data.metrics}
                transactions={data.transactions}
              />
            )}

            {/* 5. 5-Agent Architecture (15-Second Scannable + Deep Specs) */}
            <ArchitecturePipeline />

            {/* 6. Honest Engineering Scope & Limitations */}
            <HonestScope />

            {/* Showcase Footer */}
            <footer className="showcase-footer">
              <div>
                <strong>Argus Fraud Investigation Pipeline</strong> &middot; Built for Razorpay AI Buildathon (Track 2: Autonomous Agents)
              </div>
              <div className="footer-links">
                <a href="#hook">Back to top ↑</a>
                <span>&middot;</span>
                <span>Dataset: IEEE-CIS + Neo4j AuraDB</span>
                <span>&middot;</span>
                <span>Model: XGBoost + Adversarial Retraining</span>
              </div>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
