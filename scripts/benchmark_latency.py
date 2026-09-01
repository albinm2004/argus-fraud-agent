"""Argus -- latency benchmark for the full investigate() pipeline.

Answers a question nobody had measured: how long does one transaction
actually take to go through Watcher-normalized-shape -> Graph Builder ->
Pattern Analyst -> (optional Red-Team) -> Verdict? A fraud system pitched
as usable in a real webhook path needs a real number here, not a guess.

Measures two configurations separately, since Red-Team's perturbation
search (40 candidate predict_proba calls per transaction) is the
expensive step and most real traffic wouldn't run it synchronously on
every request:
  1. Without red-team (the actual webhook_receiver.py code path today --
     it calls investigate(..., run_red_team=False))
  2. With red-team enabled (what a stricter/synchronous deployment, or
     the dashboard's per-transaction robustness note, would cost)

Reports mean / p50 / p95 / p99 / max over N real held-out transactions,
using perf_counter (wall-clock, matches what a caller waiting on the
webhook response actually experiences) and warms up the lazy-loaded
model/graph/feature-store caches first so the benchmark measures steady-
state per-request cost, not one-time load cost (which is separately
reported).

Run (from repo root): PYTHONPATH=. python scripts/benchmark_latency.py
Writes docs/latency_benchmark.md.
"""
import json
import time

import numpy as np

from agents.features import build_dataset
from agents.pipeline import investigate

N_SAMPLES = 200  # per configuration -- enough for a stable p95/p99 without a long run
SEED = 42


def _percentile(values, p):
    return float(np.percentile(values, p))


def _summarize(label, times_s):
    times_ms = np.array(times_s) * 1000
    return {
        "label": label,
        "n": len(times_ms),
        "mean_ms": float(times_ms.mean()),
        "p50_ms": _percentile(times_ms, 50),
        "p95_ms": _percentile(times_ms, 95),
        "p99_ms": _percentile(times_ms, 99),
        "max_ms": float(times_ms.max()),
        "min_ms": float(times_ms.min()),
    }


def _print_summary(s):
    print(f"  {s['label']}: n={s['n']}  mean={s['mean_ms']:.1f}ms  "
          f"p50={s['p50_ms']:.1f}ms  p95={s['p95_ms']:.1f}ms  "
          f"p99={s['p99_ms']:.1f}ms  max={s['max_ms']:.1f}ms")


def main():
    print("Loading dataset + engineering features...")
    df, feature_cols, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]
    rng = np.random.default_rng(SEED)
    sample_idx = rng.choice(test_df.index, size=min(N_SAMPLES, len(test_df)), replace=False)
    sample = test_df.loc[sample_idx]

    print(f"Warming up lazy-loaded caches (model, graph, {N_SAMPLES}-row feature access)...")
    t_warm0 = time.perf_counter()
    first_row = sample.iloc[0]
    investigate(int(first_row["TransactionID"]), first_row, run_red_team=True)  # touches every code path once
    warmup_s = time.perf_counter() - t_warm0
    print(f"  first-call warmup (model load + graph load + JIT-ish caches): {warmup_s*1000:.0f}ms "
          f"-- this is a one-time cost per process, not per-request")

    print(f"\nBenchmarking {N_SAMPLES} transactions WITHOUT red-team "
          f"(the actual webhook_receiver.py code path)...")
    times_no_rt = []
    for _, row in sample.iterrows():
        txn_id = int(row["TransactionID"])
        t0 = time.perf_counter()
        investigate(txn_id, row, run_red_team=False)
        times_no_rt.append(time.perf_counter() - t0)
    summary_no_rt = _summarize("without red-team", times_no_rt)
    _print_summary(summary_no_rt)

    print(f"\nBenchmarking {N_SAMPLES} transactions WITH red-team "
          f"(40-candidate perturbation search per transaction)...")
    times_rt = []
    for _, row in sample.iterrows():
        txn_id = int(row["TransactionID"])
        t0 = time.perf_counter()
        investigate(txn_id, row, run_red_team=True)
        times_rt.append(time.perf_counter() - t0)
    summary_rt = _summarize("with red-team", times_rt)
    _print_summary(summary_rt)

    result = {
        "n_samples": N_SAMPLES,
        "seed": SEED,
        "warmup_ms": warmup_s * 1000,
        "without_red_team": summary_no_rt,
        "with_red_team": summary_rt,
    }
    with open("docs/latency_benchmark.json", "w") as f:
        json.dump(result, f, indent=2)

    with open("docs/latency_benchmark.md", "w") as f:
        f.write("# Argus -- pipeline latency benchmark\n\n")
        f.write(
            "How long one transaction actually takes through the full pipeline "
            "(Graph Builder -> Pattern Analyst -> [Red-Team] -> Verdict), measured "
            "with `time.perf_counter()` -- wall-clock, matching what a caller waiting "
            "on the webhook response experiences. Run: `scripts/benchmark_latency.py`.\n\n"
        )
        f.write(f"Measured on {N_SAMPLES} real held-out transactions (seed={SEED}), "
                f"on this machine's CPU -- these are relative numbers to show the shape "
                f"of the cost (red-team's overhead, tail latency), not a guaranteed SLA on "
                f"different hardware.\n\n")
        f.write(f"One-time warmup cost (first call in a fresh process -- loads the model, "
                f"the local graph pickle, and touches the Neo4j-availability check once): "
                f"**{warmup_s*1000:.0f}ms**. This does not repeat per request.\n\n")
        f.write("## Without red-team (the actual `webhook_receiver.py` code path today)\n\n")
        f.write("| metric | value |\n|---|---|\n")
        for k in ["mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"]:
            f.write(f"| {k} | {summary_no_rt[k]:.1f} ms |\n")
        f.write("\n## With red-team (40-candidate perturbation search per transaction)\n\n")
        f.write("| metric | value |\n|---|---|\n")
        for k in ["mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"]:
            f.write(f"| {k} | {summary_rt[k]:.1f} ms |\n")
        overhead = summary_rt["mean_ms"] - summary_no_rt["mean_ms"]
        f.write(f"\nRed-team's perturbation search adds **{overhead:.1f}ms** on average "
                f"({summary_rt['mean_ms'] / max(summary_no_rt['mean_ms'], 0.01):.1f}x the base cost) "
                f"-- consistent with why `webhook_receiver.py` runs with `run_red_team=False` "
                f"on the synchronous request path and treats it as an offline/on-demand check "
                f"instead.\n\n")
        f.write("## Known limitations of this benchmark\n\n")
        f.write("- Single-threaded, single-process, one machine -- not a load test under "
                "concurrent traffic (see the webhook receiver's own dedup-lock concurrency "
                "tests for that angle instead).\n")
        f.write("- Does not include HTTP/network overhead (signature verification, JSON "
                "parsing, ASGI request handling) -- this is pipeline-internal latency only.\n")
        f.write("- The local networkx graph fallback is what's measured here, since Neo4j "
                "has not been reachable during this project's development -- a live Neo4j "
                "round-trip would add real network latency the local pickle lookup doesn't "
                "have.\n")

    print(f"\nWrote docs/latency_benchmark.md and docs/latency_benchmark.json")


if __name__ == "__main__":
    main()
