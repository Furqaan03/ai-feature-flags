# AI Feature Flag System with Gradual Rollout & Quality Monitoring

A feature flag platform built specifically for AI-powered features, where
"working" isn't binary — it's a quality gradient. Supports percentage-based
gradual rollouts, continuously monitors output quality during the rollout, and
automatically rolls back if quality degrades below a configurable threshold,
before users are impacted.

## Why this exists

Every team uses feature flags for traditional software, where a feature either
works or throws. Almost none have adapted the pattern for AI features, which
fail on a gradient — subtly worse answers, not exceptions. This is the tooling
for shipping AI features safely: canary + auto-rollback keyed on *quality*, not
error codes.

## Architecture

```
src/flags/schema.py       AI flag schema: rollout %, quality threshold, rollback
                           trigger, baseline vs. experimental config, targeting rules
src/flags/evaluator.py    consistent-hash assignment + targeting (allow/block/segment)
                           + percentage rollout
src/quality/monitor.py    rolling quality windows (mean, P10, trend) + sustained-
                           degradation rollback trigger
src/quality/scorer.py     LLM-as-judge quality scoring (1-5)
src/rollout/stages.py     staged schedule (1->5->25->50->100%) + canary analysis
                           (advance only if experimental is statistically no worse)
src/sdk/client.py         3-5 line app integration; graceful degradation to baseline
src/api.py                FastAPI management API + auto-rollback wiring
src/alerting.py           Slack rollback notifications
```

## Design decisions

- **Rollback keys on P10, not the mean.** A feature can have a great average
  quality while badly failing the worst 10% of requests. Watching the 10th-percentile
  score catches tail failures that a mean would smooth over — the metric that
  actually predicts user-visible badness.
- **Rollback requires *sustained* degradation, with a cooldown.** A single bad
  score doesn't trigger a rollback (noise); N consecutive evals below the floor
  does. A cooldown prevents flapping between rolled-back and rolling-out.
- **Canary analysis uses a one-sided test.** The rollout advances only if
  experimental is *not significantly worse* than baseline (one-sided Mann-Whitney U).
  Requiring "provably better" would stall harmless-but-neutral improvements;
  requiring "not worse" is the correct bar for safe advancement.
- **The SDK never crashes the host app.** An unknown flag, or any exception in
  evaluation, degrades to the baseline variant. The flag layer failing must never
  take down the feature it gates.
- **Consistent-hash assignment.** Same user always sees the same variant for a
  given flag, so a user's experience is stable across requests during a rollout.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env      # OPENAI_API_KEY for LLM-judge scoring; SLACK_WEBHOOK_URL optional
uvicorn src.api:app --reload
```

## Example lifecycle

```bash
# create a flag with an AI-vs-baseline config
curl -X POST localhost:8000/flags -H "Content-Type: application/json" \
  -d '{"name": "subject-generator", "rollout_percentage": 5, "status": "rolling_out", "quality_threshold": 3.0}'

# an app asks which variant to serve for a user
curl -X POST localhost:8000/flags/subject-generator/evaluate -d '{"user_id": "u123"}' -H "Content-Type: application/json"

# the app reports back the LLM-judged quality of what it served
curl -X POST localhost:8000/flags/subject-generator/quality -d '{"score": 2.0}' -H "Content-Type: application/json"
# ... enough sustained low scores -> {"status": "rolled_back", "reason": "...", "quality": {...}}
```

## Tests

```bash
pytest tests/ -v
```

15 tests covering evaluator (off/on/targeting/consistent-assignment/percentage
distribution), rollback monitor (sustained trigger, counter reset, P10 tail
detection, trend), and canary/staged rollout (block-when-worse, allow-when-
comparable, advance/pause) — all offline, no API key required.

## Docker

```bash
docker compose up --build   # API + Postgres + Redis
```

## Status

Phases 1-3 complete (flag evaluation engine + SDK, quality monitoring with
auto-rollback, staged rollout + canary analysis) plus the management API and
Slack alerting. Phase 4's dedicated dashboard UI and Phase 5's seeded demo app
are not built — FastAPI `/docs` serves as the management surface.
