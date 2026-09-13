# Autonomous Retail Supply-Chain Recovery Agent
**Tech Zephyr 4.0 · Track 3, Problem Statement 6** — team SystemX

> Proactively detect disruptions, replan deliveries, and keep the retailer within budget/carbon caps while protecting the on-time SLA — with a real constraint verification step and a human-escalation path.

Generated: `2026-09-13T10:58:39.055315+00:00` · sim day `0` · `8` events appended

---

## 1 · System at a glance

- **Source of truth:** append-only `events` table; every command and disruption is an event with a sequence number and sim-day. All state shown below is a *projection* rebuilt by replaying the log.
- **Optimization:** OR-Tools CP-SAT picks the lowest weighted (cost/time/carbon) assignment under budget & carbon caps; greedy fallback keeps the demo moving if the solver is ever infeasible.
- **Agent graph:** `monitor → detect → retrieve → optimize → decide → execute → verify`, with an explicit replan loop after failed verification and a **human-escalation** branch after two failed attempts.
- **Reasoning:** the *decide* node writes a human-readable justification for the chosen trade-off (LLM if an API key is set, deterministic fallback otherwise). The choice itself always mirrors what the solver selected, so the trace is truthful.

---

## 2 · Live demo — two consecutive disruptions

### Baseline (seeded)

| Metric | Value | Cap |
|---|---|---|
| Orders at risk | 0 | — |
| On-time delivery | 100.0% | ≥ 95% |
| Committed cost | 6750.0 | ≤ 9000.0 |
| Committed carbon | 1012.0 | ≤ 1600.0 |
| Budget headroom | 2250.0 | > 0 |
| Carbon headroom | 588.0 | > 0 |

### Disruption #1 · shipment_delay: S-3 (O-3) delayed +7 days

- `#1` d0 **shipment_delay** {`shipment_id`: `S-3`, `delay_days`: 7}

### Agent run #1 — replan to re-secure O-3


| Step | Day | Detail |
|---|---|---|
| monitor | 0 | Monitored 5 orders, 5 shipments. |
| detect | 0 | 1 constraint violation(s) detected |
| retrieve | 0 | Retrieved 9 candidate plan(s) |
| optimize | 0 | Solver status: optimal; selected 1 plan(s) |
| decide | 0 | Decision: PLAN-O-3-purchase-V-MUM-R_MUM_MUM (deterministic-fallback) · \`PLAN-O-3-purchase-V-MUM-R_MUM_MUM\` |
| execute | 0 | Executed 2 command(s) |
| verify | 0 | Constraints satisfied ✓ · **PASS** |

### State after recovery #1

- at-risk orders: 0 · issues: []
- committed cost **5250.0** / carbon **652.0** (headroom 3750.0/948.0)

### Disruption #2 · shipment_loss: S-PO-0 lost; vendor V-MUM cap → 0

- `#4` d0 **shipment_loss** {`shipment_id`: `S-PO-0`}
- `#5` d0 **vendor_capacity_drop** {`vendor_id`: `V-MUM`, `new_capacity`: 0}

### Agent run #2 — replan after loss + capacity drop


| Step | Day | Detail |
|---|---|---|
| monitor | 0 | Monitored 5 orders, 6 shipments. |
| detect | 0 | 1 constraint violation(s) detected |
| retrieve | 0 | Retrieved 8 candidate plan(s) |
| optimize | 0 | Solver status: optimal; selected 1 plan(s) |
| decide | 0 | Decision: PLAN-O-3-allocate-WH-CHN-R_CHN_MUM (deterministic-fallback) · \`PLAN-O-3-allocate-WH-CHN-R_CHN_MUM\` |
| execute | 0 | Executed 2 command(s) |
| verify | 0 | Constraints satisfied ✓ · **PASS** |

### Final state after recovery #2

- at-risk orders: 0 · issues: []
- committed cost **6850.0** / carbon **1052.0** (headroom 2150.0/548.0)

### Key figures

| Metric | Value | Cap |
|---|---|---|
| Orders at risk | 0 | — |
| On-time delivery | 100.0% | ≥ 95% |
| Committed cost | 6850.0 | ≤ 9000.0 |
| Committed carbon | 1052.0 | ≤ 1600.0 |
| Budget headroom | 2150.0 | > 0 |
| Carbon headroom | 548.0 | > 0 |

**No at-risk orders remain after recovery.**

---

## 3 · Constraint verification & escalation

- `verify` executes a **real check** over the rebuilt projection, not just the optimizer output. Any constraint violation (order shortfall, cap breach, over-committed vendor capacity) loops the graph back to `retrieve` with the offending candidates excluded.
- If a second replan fails, the graph reaches `escalate_to_human`: the audit log is preserved and an operator alert is raised. The scenario below never needs it, but the path is exercised by `tests/unit/test_optimizer.py` and `tests/scenario/test_two_disruptions.py`.

## 4 · Runbook

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000   # API
cd frontend && npm install && npm run dev          # dashboard :5173
python tools/report.py --demo                      # regenerate this evidence
python -m pytest tests -q                          # 18 checks
docker compose up                                  # full stack: Postgres + API + dashboard
```
