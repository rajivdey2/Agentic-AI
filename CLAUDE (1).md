# CLAUDE.md — Autonomous Retail Supply Chain Recovery Agent
### Tech Zephyr 4.0 · Agentic AI Hackathon (IIT Bhubaneswar) · Track 3, Problem Statement 6

This file is the build context for Claude Code sessions on this project. Keep it updated as
decisions change — treat it as the single source of truth for architecture, scope, and demo plan.

---

## 1. Why this problem statement

Of the 11 statements, PS6 (Retail Supply Chain Recovery) is the hardest to execute well, and the
one most teams will underestimate or avoid:

- **Genuine optimization, not just retrieval.** Most other tracks (healthcare docs, education
  planning, resume tailoring) reduce to RAG + reconciliation + drafting. PS6 requires a real
  constrained-optimization step (cost / delivery-time / carbon trade-offs), which is algorithmically
  harder to get right and much harder to fake with a prompt chain.
- **Multi-service state, not single-document state.** The agent has to keep four moving parts
  consistent at once — inventory, shipments, vendors, cost/carbon — which forces real state
  management and gives the strongest possible demo of "persistent task state" and "adaptation."
- **Cascading failure is built into the problem.** The rubric explicitly rewards "a failure,
  conflict, or changed-condition scenario demonstrable during judging" (15% adaptation) — PS6 asks
  for *two* disruptions in sequence, which is the single best fit in the whole list for that
  criterion and for the 25% "agentic workflow & autonomy" criterion.
- **It rewards backend/systems depth over ML depth.** No multimodal parsing, no clinical/security
  domain expertise needed — the hard part is architecture and correctness, which is a better use of
  hackathon hours than trying to get a vision model or a security KB right from scratch.

**Working assumption:** the organizers' "suggested sandbox tools" are a spec, not a provided API —
budget time to build the simulated environment ourselves (see §7). If Tech Zephyr issues real
sandbox endpoints at kickoff, swap them in behind the same tool interface with minimal rework.

---

## 2. Problem restatement (from the official PDF)

Build an autonomous supply-chain recovery agent that maintains service objectives (on-time
delivery, cost, carbon) when inventory, shipment, vendor, or demand conditions change.

Required workflow: monitor inventory/shipment state → detect a disruption or constraint violation →
investigate alternative vendors/routes/allocations → use optimization tools to compare feasible
actions → execute a simulated rerouting/purchase/allocation/transfer → verify the resulting state →
replan when the chosen alternative becomes unavailable or another disruption occurs.

---

## 3. Win conditions (rubric → what we build to satisfy it)

| Criterion | Weight | What proves it |
|---|---|---|
| Agentic workflow & autonomy | 25% | Explicit state graph (not a linear script) with conditional loop-back edges; agent chooses actions from runtime state, not hardcoded per-scenario logic |
| Tool/environment interaction | 15% | 5+ distinct tools (inventory, shipment, vendor, route/cost/carbon calculator, state-changing endpoints) actually called, not stubbed |
| Adaptation & failure recovery | 15% | Two chained live disruptions in the demo, each forcing a real replan with a different outcome |
| Technical implementation | 15% | Real LP/CP optimizer (not a heuristic sort), event-sourced state (replayable, auditable), automated scenario tests |
| Problem relevance & innovation | 10% | Cost/carbon-aware trade-off reasoning surfaced to the user, not just "found a workaround" |
| Prototype functionality & UX | 10% | Live dashboard: state, decision trace, KPIs, manual disruption trigger |
| Evaluation, verification & robustness | 10% | Post-action verification step is a real check against constraints, with an escalation path when it fails twice |

Keep this table visible during build — anything you're building that doesn't map to a row is scope
creep.

---

## 4. Architecture overview

Core idea: treat every state change (reroute, purchase, allocation, transfer) as an **event**, and
derive all "current state" views from the event log. This is a CQRS / event-sourcing split — it
gives you three things this problem specifically needs for free: an audit trail (verification
criterion), point-in-time replay (great for the demo's "final outcome" recap), and a clean
read/write separation between the agent's *planning* step (reads projections) and its *execution*
step (writes commands → events).

```
                     ┌────────────────────────┐
   Dashboard  ◄───── │   Query API (reads)     │ ◄── projections rebuilt from event log
  (React/TS)         │  inventory / shipment /  │
                      │  vendor / KPI views      │
                      └───────────▲──────────────┘
                                  │ replays
                      ┌───────────┴──────────────┐
                      │      Event Store (PG)      │  ← append-only, source of truth
                      └───────────▲──────────────┘
                                  │ commands emit events
        ┌─────────────────────────┴─────────────────────────┐
        │              Agent Orchestrator (LangGraph)         │
        │  Monitor → Detect → Retrieve Alternatives →         │
        │  Optimize → Decide → Execute → Verify → (loop)      │
        └───────┬───────────────┬───────────────┬────────────┘
                │               │                │
        ┌───────▼─────┐ ┌───────▼──────┐ ┌───────▼────────┐
        │ Optimizer    │ │ SimWorld API │ │ Disruption      │
        │ (OR-Tools)   │ │ (FastAPI)    │ │ Injector        │
        └──────────────┘ └──────────────┘ └─────────────────┘
```

---

## 5. Recommended stack

Pick tools you can move fastest in — hackathon judging rewards a working, well-instrumented system
over an unfamiliar "impressive" one.

- **Backend / agent:** Python, FastAPI, LangGraph for the state-graph orchestration (its conditional
  edges map directly onto the "replan on failure" requirement), Claude/GPT API for the reasoning
  and justification steps only — every deterministic step (cost calc, constraint check, optimizer)
  stays in plain code so the system can't be dismissed as "just a prompt chain."
- **Event store / projections:** PostgreSQL. One `events` table (append-only) + materialized
  projection tables rebuilt on write.
- **Optimizer:** OR-Tools (CP-SAT or linear solver) for allocation/routing choice among a bounded
  candidate set. PuLP is an acceptable lighter-weight fallback if OR-Tools setup eats too much time.
- **Frontend:** React + TypeScript + Tailwind + Recharts, polling or WebSocket for live updates.
- **Packaging:** Docker Compose for a self-contained, network-independent demo (don't depend on a
  live cloud deploy during judging). Optionally also deploy backend/frontend to Render/Vercel so
  judges can poke at it afterward.
- **Tests/CI:** GitHub Actions running the scenario test suite (§9) on every push — this is a cheap
  way to visibly back the "robustness" rubric line.

---

## 6. Repository structure

```
/agent            orchestration graph, tool wrappers, prompts, reasoning/justification layer
  /graph.py        LangGraph state machine definition
  /tools.py        typed wrappers around SimWorld + optimizer calls
  /nodes/          monitor.py, detect.py, retrieve.py, optimize.py, decide.py, execute.py, verify.py
/simworld          simulated logistics environment (its own FastAPI service)
  /events.py       event definitions + append-only store
  /projections.py  inventory / shipment / vendor / KPI read models
  /disruptions.py  disruption injector, incl. manual "chaos" endpoint for live demo
  /api.py
/optimizer         allocation/routing solver, cost & carbon calculators
/frontend          React dashboard
/tests
  /unit
  /scenario        end-to-end: baseline → disruption 1 → replan → disruption 2 → replan → verify
/docs
  architecture.png (export of the diagram above)
  demo-script.md
  evidence-report.md   (auto-generated change/decision log from a demo run)
CLAUDE.md
docker-compose.yml
```

---

## 7. SimWorld: the simulated environment

Since the organizers only *suggest* sandbox tools, build a small self-contained world:

**Entities:** warehouses (location, capacity), SKUs (inventory per warehouse), vendors (capacity,
reliability score, lead time, unit cost), shipments (origin, destination, route, ETA, status),
active customer orders (SKU, quantity, deadline).

**Simulated clock:** accelerated — e.g. 1 real minute = 1 simulated day — so a multi-day recovery
plan is visible within a demo slot.

**Tools exposed to the agent** (map 1:1 to the problem statement's suggested list):
- `get_inventory_state()`, `get_shipment_state()`, `get_vendor_options(sku, constraints)`
- `get_alternative_routes(shipment_id)`
- `calculate_cost_carbon(plan)` — deterministic, called by both optimizer and verifier
- `reroute_shipment(...)`, `place_order(...)`, `allocate_inventory(...)`, `transfer_stock(...)` —
  each emits an event, never mutates state directly

**Disruption injector — the most demo-critical piece.** Don't rely on random timing during judging.
Build a manual trigger (dashboard button or CLI) that fires one of: vendor capacity drop, shipment
delay/loss, route closure, demand spike, carbon-cap breach. This is what lets you guarantee the
required "failure, conflict, or changed-condition scenario" happens exactly when you want it to,
twice, in front of judges.

---

## 8. Agent workflow (LangGraph state graph)

Nodes, matching the required workflow almost verbatim:

```
monitor → detect_violation → [no violation: loop to monitor]
                            → [violation]: retrieve_alternatives
                                          → optimize_candidates
                                          → decide_action
                                          → execute_action
                                          → verify_outcome → [pass]: monitor
                                                            → [fail]: retrieve_alternatives (replan)
                                                            → [fail twice]: escalate_to_human
```

- `detect_violation` compares live projections against the objective constraints (on-time %,
  budget, carbon cap) — this is what "monitoring" actually means here, not a poll-and-print loop.
- `retrieve_alternatives` queries vendor/route options bounded to a small candidate set (≤ ~15) so
  the optimizer stays fast enough for a live demo.
- `optimize_candidates` runs the OR-Tools solver against cost/delivery/carbon weights; returns a
  ranked list with the trade-offs made explicit (this ranked, justified output is what makes the
  system look genuinely agentic rather than a rules engine).
- `decide_action` is where the LLM reasoning step earns its place: given the ranked candidates, it
  picks one and writes a short natural-language justification — this becomes the "evidence-backed"
  trail the rubric's verification criterion wants.
- `execute_action` issues the command, which emits an event; state is now changed.
- `verify_outcome` re-reads the projection and checks it actually satisfies constraints. A failed
  verification loops back into `retrieve_alternatives` with the failed candidate excluded — this is
  the literal "replan when the chosen alternative becomes unavailable" requirement.
- `escalate_to_human` exists so the system never silently pretends a problem is solved when it
  isn't — matches the general agentic principle of "verification against objective constraints."

---

## 9. Verification & evaluation harness

Build this early, not as an afterthought — it's worth 10% on its own and de-risks the live demo.

- **Scenario tests** (`/tests/scenario`): scripted event sequences that assert the agent reaches a
  constraint-satisfying state after 1 and after 2 chained disruptions, and that it does NOT re-pick
  an alternative that verification already rejected.
- **Property checks:** every executed action has a corresponding event; every projection can be
  rebuilt from the event log alone (replay test) — this is what actually proves the "audit trail /
  verification" story to a technical judge, not just a claim in the slides.
- **KPI diffing:** before/after comparison (on-time %, total cost, total carbon) computed from
  projections, shown on the dashboard and logged to `docs/evidence-report.md`.

---

## 10. Demo script (Goal → Decision → Action → Intermediate Result → Adaptation → Final Outcome)

1. **Goal:** dashboard opens on a baseline plan — active orders, current routes, target: 95%
   on-time, budget and carbon caps shown as gauges.
2. **Decision (disruption 1):** press the chaos button → vendor capacity drop on an in-flight order.
   Agent detects the violation live; decision trace panel shows candidates and the chosen trade-off.
3. **Action:** agent executes the reroute; dashboard updates the shipment path and cost/carbon
   gauges in real time.
4. **Intermediate result:** verification pass shown explicitly ("constraints satisfied ✓") with the
   new KPIs.
5. **Adaptation (disruption 2):** press chaos button again → the *just-chosen* alternate vendor also
   fails. Agent must replan again, this time under a smaller candidate set, and may have to accept a
   visible trade-off (e.g., a 1-day SLA slip to stay under the carbon cap) — narrate this as the
   payoff of the whole approach: the system reasons about trade-offs instead of just retrying.
6. **Final outcome:** recap screen — event log / audit trail, before/after KPI table, and the
   auto-generated evidence report.

Rehearse this exact sequence until it's reliable without narration — live LLM calls should have a
timeout + deterministic fallback (cheapest ranked candidate) so a slow API response never stalls
the room.

---

## 11. Build phases

Sequence, not fixed days — compress or expand against the actual clock once the schedule is known.

1. **Skeleton:** Postgres event store + SimWorld entities/seed data + projections rebuild-from-log.
2. **Read APIs:** inventory/shipment/vendor/route/cost-carbon endpoints working and seed-data-tested.
3. **Agent graph v1:** LangGraph skeleton wired to real tools, no optimizer yet (dumb "first valid
   candidate" decision) — get the full loop (including the replan edge) working end-to-end early.
4. **Optimizer:** swap in OR-Tools; verify ranked output changes the agent's decisions sensibly.
5. **Disruption injector + manual trigger.**
6. **Scenario test suite** (§9) — write these against the real graph, not mocks.
7. **Dashboard:** state view → decision trace → KPI charts → chaos-trigger controls, in that order.
8. **Demo rehearsal + evidence report generator + docker-compose packaging.**
9. **Submission packaging** (see §12).

---

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Optimizer scope creep (full MILP over huge candidate sets) | Cap candidate set size; OR-Tools CP-SAT with a short time limit and a heuristic fallback |
| LLM latency/failure during live demo | Timeout + deterministic fallback decision; pre-warm the API before judging starts |
| Demo relies on random timing and doesn't fire on cue | Manual chaos-trigger endpoint is mandatory, not optional |
| Judges read it as "just a prompt chain" | Lead the walkthrough with the state graph and the replay/audit trail — both are hard to fake |
| Running out of time on frontend polish | Dashboard only needs 4 panels (state, decision trace, KPIs, chaos controls) — resist adding more |

---

## 13. Submission checklist

- [ ] Demo video named `Teamname_video_agentic`, shows Goal → Decision → Action → Intermediate
      Result → Adaptation → Final Outcome explicitly
- [ ] GitHub repo named per `Teamname_Github/Agentic` convention, README with setup + architecture
      diagram
- [ ] Runnable version (docker-compose up) — encouraged, not required, but strengthens "prototype
      functionality" score
- [ ] Presentation summary: approach, final solution, challenges, conclusion
- [ ] Evidence/change report from a real recorded run (not hand-written)
- [ ] Re-check every row in the §3 rubric table before submitting
