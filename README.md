# Autonomous Retail Supply-Chain Recovery Agent

**Tech Zephyr 4.0 · Track 3 · Problem Statement 6**

An event-sourced retailer simulator + a self-healing agent that detects supply
disruptions, replans deliveries with an OR-Tools optimizer, real constraint
verification, optional LLM narration, and a human-escalation path.

```
clock ──▶ append-only event log ──▶ projections (state/KPIs/issues)
                    ▲                      │
    agent graph     │                      ▼
  monitor→detect→retrieve→optimize→decide→execute→verify→(end|replan|escalate)
                    │                      │
                    └── commands ──────────┘
```

## Stack

- **SimWorld**: SQLAlchemy + SQLite (default) or Postgres via `DATABASE_URL`.
  The `events` table is the single source of truth; nothing mutates directly.
- **Optimizer**: OR-Tools **CP-SAT** (weighted cost/time/carbon under budget &
  carbon caps) with a greedy fallback for full coverage.
- **Agent**: **LangGraph** state machine with an in-memory checkpointer, typed
  tools, a deterministic replan loop on failed verification, and an
  `escalate_to_human` branch after two failures.
- **LLM (optional)**: `decide` narrates the chosen trade-off via
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`; a deterministic fallback keeps the demo
  moving when no key is set.
- **Frontend**: React + Vite + Tailwind, live-updating KPIs, orders, shipments,
  inventory, decision trace, chaos triggers and the audit log.

## Quick start

```bash
pip install -r requirements.txt

# 1. API
python -m uvicorn main:app --reload --port 8000

# 2. Dashboard (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api → :8000)

# 3. Tests
python -m pytest tests -q    # 18 checks
```

## Live demo (the "chaos" story)

The dashboard **Chaos & recovery** panel fires live disruptions; the agent
reacts each time. The scripted two-disruption scenario used for judging:

1. `shipment_delay` on `S-3` (+7 days) → agent cancels the delayed lane and
   re-buys from a same-city vendor (big cost/carbon **saving**, deadline kept).
2. `shipment_loss` on O-3's new shipment **and** `V-MUM capacity → 0` → agent
   re-secures O-3 from warehouse inventory via `R_CHN_MUM`.

Reproduce it and generate the submission evidence packet:

```bash
python tools/report.py --demo
# → evidence/evidence.json   (full machine-readable packet)
#   evidence/report.md       (submission report: events, KPIs, agent traces)
```

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/state`, `/kpis`, `/inventory`, `/shipments`, `/orders`, `/vendors`, `/routes`, `/events` | Read-side projections |
| GET | `/candidates?order_id=` | Ranked alternative plans for at-risk orders |
| POST | `/commands/reroute`, `/cancel`, `/place_order`, `/allocate`, `/transfer` | Commands (each appends an event) |
| POST | `/disruptions/trigger` (6 types), GET `/disruptions/types` | Chaos injector |
| POST | `/agent/run`, GET `/agent/trace/{id}` | Run agent, read checkpoint trace |
| POST | `/reset` | Clear log + reseed |

## Configuration (env)

| Var | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/simworld.db` | `postgresql+psycopg://…` for Postgres |
| `SIM_DAY_SECONDS` | `60` | 1 real second = 1/60 sim day |
| `OBJ_WEIGHT_COST/TIME/CARBON` | `1.0 / 0.5 / 0.3` | Optimizer objective weights |
| `CANDIDATE_CAP` | `15` | Max candidates per at-risk order |
| `VERIFY_MAX_ATTEMPTS` | `2` | Replans before escalation |
| `LLM_TIMEOUT_SECONDS` | `12` | LLM decide timeout |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | `""` | Optional LLM narration |
| `GROQ_API_KEY` | `""` | Optional Groq narration (OpenAI-compatible) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model id |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq endpoint |

## Docker (Postgres flavour)

```bash
docker compose up --build    # db + api :8000 + web :5173
```

## Project layout

```
agent/          LangGraph workflow (context, state, tools, llm, graph, nodes/, …)
optimizer/      calculators, candidate builder, CP-SAT + greedy solvers
simworld/       events (append-only), seed, projections, world commands,
                disruptions, FastAPI app
tests/          unit + two-disruption scenario suites
tools/report.py evidence generator
frontend/       Vite + React dashboard
data/           SQLite file (git-ignored)
```