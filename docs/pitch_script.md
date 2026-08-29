# Pitch video script (5 minutes)

Working draft — read through once, adjust to your own voice, then record.
Time budget adds to ~5:00; pad/trim in the demo section since that's the
part that varies each take.

Suggested recording setup: two terminals side by side (one running
`scripts/demo_replay.py`, one idle for a quick `git log`/`pytest` proof),
plus the Streamlit dashboard in a browser tab. Screen-record the terminal
and dashboard, voice over live rather than reading verbatim.

## 0:00 - 0:25 — Hook + problem

"Fraud detection isn't just 'is this score above a threshold' — a real
system has to survive an adversary who's *reading your model's output* and
adjusting. I built Argus: a multi-agent fraud investigation pipeline for
Razorpay-style transactions that scores, explains, red-teams itself, and
logs every decision — and I'm going to show you it actually working, not
just describe it."

## 0:25 - 1:00 — Architecture, fast

Show `docs/architecture.md`'s diagram or just narrate over the repo tree:

"Five agents, wired as a real LangGraph state machine, not just functions
called in sequence: Watcher verifies and normalizes the incoming
transaction event, Graph Builder checks for shared-card/address rings
against a live Neo4j graph — falling back to a local graph if Neo4j's
unreachable — Pattern Analyst scores it with a hardened XGBoost model,
Red-Team optionally checks whether a fraudster could perturb their way
under the threshold, and Verdict renders block/flag/allow with a real
per-feature SHAP explanation and logs it to an audit trail."

## 1:00 - 1:15 — The data + the honest numbers

"Trained on IEEE-CIS's real 590K-transaction fraud dataset, 3.5% fraud
rate, split by time — not shuffled — so there's no leakage from the
future into training. Held-out: 91% ROC-AUC, 50% precision, 47% recall.
I'm not rounding those up — they're in `docs/results.md` with the exact
methodology."

*(Swap in your actual current numbers from docs/results.md /
hardening_metrics.json before recording — these are as of the last
training run.)*

## 1:15 - 2:45 — Live demo (the core of the video)

Run, on camera:

```
PYTHONPATH=. python scripts/demo_replay.py --n-fraud 2 --n-legit 1 --seed <pick one that lands a block and a miss>
```

Narrate as it runs:

- "This isn't a mocked demo — `verify_signature` is doing a real
  HMAC-SHA256 check on a Razorpay-shaped webhook body, exactly like it
  would for a live payment. Watch it reject a tampered copy of the same
  payload." (point at the tampered-body line)
- When a verdict prints: "Here's a transaction the model blocks — and
  here's *why*, not just a score: five SHAP-attributed features, ranked
  by how much they moved the risk score, plus a graph signal if this
  transaction shares a card or address with others."
- Then flip to the Streamlit dashboard (`streamlit run app/dashboard.py`),
  click a flagged transaction, and show the same evidence chain rendered
  for a non-technical reviewer: "This is what a fraud analyst would
  actually see and act on."

If you have time, also show one it misses: "And I'm showing you a miss on
purpose — recall is 47%, not 100%, and pretending otherwise in a demo
would be dishonest. The `[MISS]` cases are exactly as real as the
`[correct]` ones."

## 2:45 - 3:30 — Adversarial hardening (the differentiator)

"Here's the part most fraud-detection demos skip: I asked, if a
fraudster could see the model's score and nudge their transaction's
features — amount, velocity signals, timing — could they evade it? Baseline
model: yes, 32.8% of the time, even on transactions it originally caught.
So I added adversarial training — generating perturbed-but-correctly-
labeled examples and retraining on them. Evasion rate on the same attack
family: zero. Cost: 0.3 points of recall. That tradeoff, and the honest
scope of what 'zero evasion' actually means, is in
`docs/hardening_results.md`."

## 3:30 - 4:15 — Engineering rigor / honest bugs found and fixed

"I want to show you this isn't a weekend script — it's been through real
end-to-end testing, and that testing found real bugs. Two examples,
both documented in the README:

1. Pulling a single transaction row out of a mixed-dtype DataFrame
   silently corrupted its ID from an int to a float — broke every graph
   lookup until I tested the *whole pipeline*, not just each agent in
   isolation.
2. The ring-detection graph excluded popular hub addresses to stop the
   graph from collapsing into one giant fake 'ring' — but I'd missed that
   popular *cards* do the same thing. One demo run showed a transaction
   'linked' to over 13,000 fraud cases — obviously wrong. Found it,
   fixed it, added a regression test so it can't come back quietly."

(Optionally run `PYTHONPATH=. python -m pytest tests/ -v` on camera —
12 passing tests, ~9 seconds.)

## 4:15 - 4:45 — Live integrations

"This runs against real infrastructure, not a toy setup: real Razorpay
test-mode API keys — the Watcher's signature check is the same one a
production webhook receiver would run — and a real Neo4j AuraDB graph
database for the live ring-detection path, with an automatic fallback to
a local graph if it's unreachable, because a fraud system shouldn't go
dark just because one dependency is slow."

## 4:45 - 5:00 — Close

"Everything you just saw is in the public repo: the code, the honest
metrics, the bugs I found and fixed, and the known limitations I *didn't*
solve, written down rather than hidden. That's Argus."

---

## Notes for recording day

- Confirm `python scripts/smoke_test_integrations.py` shows both Razorpay
  and Neo4j OK before recording, so a live-integration claim on camera is
  backed by a fresh check.
- Pick a `--seed` for `demo_replay.py` ahead of time that reliably lands
  one `block` and one `MISS` — reproducible, not "hope it works live."
- Keep `docs/results.md`, `docs/hardening_results.md`, and
  `docs/architecture.md` open in tabs in case you want to point the
  camera at a specific number instead of just saying it.
