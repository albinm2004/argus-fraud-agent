# Argus -- pipeline latency benchmark

How long one transaction actually takes through the full pipeline (Graph Builder -> Pattern Analyst -> [Red-Team] -> Verdict), measured with `time.perf_counter()` -- wall-clock, matching what a caller waiting on the webhook response experiences. Run: `scripts/benchmark_latency.py`.

Measured on 200 real held-out transactions (seed=42), on this machine's CPU -- these are relative numbers to show the shape of the cost (red-team's overhead, tail latency), not a guaranteed SLA on different hardware.

One-time warmup cost (first call in a fresh process -- loads the model, the local graph pickle, and touches the Neo4j-availability check once): **694ms**. This does not repeat per request.

## Without red-team (the actual `webhook_receiver.py` code path today)

| metric | value |
|---|---|
| mean_ms | 8.5 ms |
| p50_ms | 8.1 ms |
| p95_ms | 10.6 ms |
| p99_ms | 15.9 ms |
| max_ms | 43.1 ms |

## With red-team (40-candidate perturbation search per transaction)

| metric | value |
|---|---|
| mean_ms | 9.7 ms |
| p50_ms | 9.3 ms |
| p95_ms | 11.9 ms |
| p99_ms | 18.9 ms |
| max_ms | 31.7 ms |

Red-team's perturbation search adds **1.2ms** on average (1.1x the base cost) -- consistent with why `webhook_receiver.py` runs with `run_red_team=False` on the synchronous request path and treats it as an offline/on-demand check instead.

## Known limitations of this benchmark

- Single-threaded, single-process, one machine -- not a load test under concurrent traffic (see the webhook receiver's own dedup-lock concurrency tests for that angle instead).
- Does not include HTTP/network overhead (signature verification, JSON parsing, ASGI request handling) -- this is pipeline-internal latency only.
- The local networkx graph fallback is what's measured here, since Neo4j has not been reachable during this project's development -- a live Neo4j round-trip would add real network latency the local pickle lookup doesn't have.
