"""Evidence report generator — submission packet for the simulation.

Writes `evidence/evidence.json` (full machine-readable packet) and
`evidence/report.md` (human-readable submission report) from the live event
log, projections and the agent's checkpointed trace.

Usage:
    python tools/report.py            # dump current DB state into evidence/
    python tools/report.py --demo     # reset world, run the two-disruption
                                      # self-healing demo, then generate evidence/
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "evidence"

from agent.graph import run_agent
from simworld import disruptions, world
from simworld.events import EventStore

FACTS = {
    "title": "Autonomous Retail Supply-Chain Recovery Agent",
    "event": "Tech Zephyr 4.0 · Track 3, Problem Statement 6",
    "team": "SystemX",
    "architecture": "Event-sourced quantum of truth · OR-Tools CP-SAT optimizer · LangGraph agent",
    "objective": (
        "Proactively detect disruptions, replan deliveries, and keep the retailer within "
        "budget/carbon caps while protecting the on-time SLA — with a real constraint "
        "verification step and a human-escalation path."
    ),
}


def demo_payload(store: EventStore) -> dict:
    """Fire the mandatory two-disruption scenario and capture agent runs."""
    world.reset_world()
    steps = []
    baseline = world.get_state()

    def mark(label: str, payload: dict) -> None:
        payload["label"] = label
        steps.append(payload)

    d1 = disruptions.build_disruption("shipment_delay",
                                      {"shipment_id": "S-3", "delay_days": 7}).apply()
    mark("Disruption #1 · shipment_delay: S-3 (O-3) delayed +7 days", {"events": d1})
    run1 = run_agent()
    mark("Agent run #1 — replan to re-secure O-3", run_state(run1))
    mark("State after recovery #1", {"state": world.get_state()})

    st = world.get_state()
    o3_ship = next((s for s in st["shipments"].values()
                    if s["order_id"] == "O-3" and s["status"] == "in_transit"), None)
    if o3_ship is None:
        raise RuntimeError("expected an in-transit O-3 shipment after recovery #1")
    d2 = disruptions.build_disruption("shipment_loss",
                                      {"shipment_id": o3_ship["id"]}).apply()
    d2b = disruptions.build_disruption("vendor_capacity_drop",
                                       {"vendor_id": "V-MUM", "new_capacity": 0}).apply()
    mark(f"Disruption #2 · shipment_loss: {o3_ship['id']} lost; vendor V-MUM cap → 0",
         {"events": d2 + d2b})
    run2 = run_agent()
    mark("Agent run #2 — replan after loss + capacity drop", run_state(run2))
    mark("Final state after recovery #2", {"state": world.get_state()})

    return {"steps": steps, "runs": [dict(run1), dict(run2)], "baseline": baseline}


def run_state(state: dict) -> dict:
    """Trim an AgentState to the fields the evidence packet needs."""
    solver = state.get("solver")
    return {
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "trace": state.get("trace", []),
        "decision": state.get("decision"),
        "verification": state.get("verification"),
        "solver": {
            "status": solver.get("status"),
            "selected": solver.get("selected", []),
            "ranked": solver.get("ranked", []),
            "excluded": solver.get("excluded", []),
        } if solver else None,
        "message": state.get("message"),
        "day": state.get("day"),
    }


def collect(store: EventStore, runs: list[dict] | None) -> dict:
    st = world.get_state(store)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facts": FACTS,
        "sim_day": st["sim_day"],
        "event_count": st["event_count"],
        "events": store.events(),
        "kpis": st["kpis"],
        "issues": st["issues"],
        "risk_orders": st["risk_orders"],
        "state": st,
        "runs": runs or [],
    }


def write_json(packet: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "evidence.json"
    path.write_text(json.dumps(packet, indent=2, default=str, sort_keys=True), encoding="utf-8")
    return path


def md_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def kpi_table(k: dict) -> str:
    rows = [
        ("Orders at risk", k.get("at_risk_orders"), "—"),
        ("On-time delivery", f"{k.get('on_time_rate', 0) * 100:.1f}%", f"≥ {k.get('on_time_target', 0.95) * 100:.0f}%"),
        ("Committed cost", k.get("total_cost"), f"≤ {k.get('budget_cap')}"),
        ("Committed carbon", k.get("total_carbon"), f"≤ {k.get('carbon_cap')}"),
        ("Budget headroom", k.get("remaining_budget"), "> 0"),
        ("Carbon headroom", k.get("remaining_carbon"), "> 0"),
    ]
    out = ["| Metric | Value | Cap |", "|---|---|---|"]
    for label, val, cap in rows:
        out.append(f"| {label} | {md_cell(str(val))} | {md_cell(str(cap))} |")
    return "\n".join(out)


def trace_md(run: dict) -> str:
    lines = ["| Step | Day | Detail |", "|---|---|---|"]
    for t in run.get("trace", []):
        detail = md_cell(t.get("summary", ""))
        if "choice" in t:
            detail += f" · \`{t.get('choice')}\`"
        if t.get("passed") is not None:
            detail += f" · **{'PASS' if t['passed'] else 'FAIL'}**"
        if t.get("issues_after"):
            detail += f" · issues: {md_cell(', '.join(t['issues_after']))}"
        lines.append(f"| {t.get('step', '')} | {t.get('day', '')} | {detail} |")
    return "\n".join(lines)


def write_md(packet: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "report.md"
    lines: list[str] = []
    A = lines.append

    A(f"# {FACTS['title']}")
    A(f"**{FACTS['event']}** — team {FACTS['team']}")
    A("")
    A(f"> {FACTS['objective']}")
    A("")
    A(f"Generated: `{packet['generated_at']}` · sim day `{packet['sim_day']}` · "
      f"`{packet['event_count']}` events appended")
    A("")
    A("---")
    A("")
    A("## 1 · System at a glance")
    A("")
    A("- **Source of truth:** append-only `events` table; every command and disruption "
      "is an event with a sequence number and sim-day. All state shown below is a "
      "*projection* rebuilt by replaying the log.")
    A("- **Optimization:** OR-Tools CP-SAT picks the lowest weighted "
      "(cost/time/carbon) assignment under budget & carbon caps; greedy fallback keeps "
      "the demo moving if the solver is ever infeasible.")
    A("- **Agent graph:** `monitor → detect → retrieve → optimize → decide → "
      "execute → verify`, with an explicit replan loop after failed verification and a "
      "**human-escalation** branch after two failed attempts.")
    A("- **Reasoning:** the *decide* node writes a human-readable justification for the "
      "chosen trade-off (LLM if an API key is set, deterministic fallback otherwise). "
      "The choice itself always mirrors what the solver selected, so the trace is "
      "truthful.")
    A("")
    A("---")
    A("")
    A("## 2 · Live demo — two consecutive disruptions")
    A("")
    A("### Baseline (seeded)")
    A("")
    A(kpi_table(packet.get("baseline", packet["state"])["kpis"]))
    A("")

    for step in packet.get("steps", []):
        label = step["label"]
        A(f"### {label}")
        A("")
        if "runs" not in step and "events" in step:
            for ev in step["events"]:
                simple = json.dumps(ev["payload"], default=str).replace('"', '`')
                A(f"- `#{ev['seq']}` d{ev['day']} **{ev['type']}** {md_cell(simple)}")
        if "state" in step:
            st_ = step["state"]
            k = st_["kpis"]
            issues = st_["issues"]
            A("- at-risk orders: "
              f"{k['at_risk_orders']} · issues: {md_cell(str([i.get('kind') for i in issues]))}")
            A(f"- committed cost **{k['total_cost']}** / carbon **{k['total_carbon']}** "
              f"(headroom {k['remaining_budget']}/{k['remaining_carbon']})")
        if "run_id" in step:
            A("")
            A(trace_md(step))
        A("")

    A("### Key figures")
    A("")
    final = packet.get("steps", [])[-1]
    A(kpi_table(final["state"]["kpis"]))
    A("")

    risks = packet["state"]["risk_orders"]
    if risks:
        A("At-risk orders after recovery: " + ", ".join(r["order_id"] for r in risks))
    else:
        A("**No at-risk orders remain after recovery.**")
    A("")

    A("---")
    A("")
    A("## 3 · Constraint verification & escalation")
    A("")
    A("- `verify` executes a **real check** over the rebuilt projection, not just the "
      "optimizer output. Any constraint violation (order shortfall, cap breach, "
      "over-committed vendor capacity) loops the graph back to `retrieve` with the "
      "offending candidates excluded.")
    A("- If a second replan fails, the graph reaches `escalate_to_human`: the audit log "
      "is preserved and an operator alert is raised. The scenario below never needs it, "
      "but the path is exercised by `tests/unit/test_optimizer.py` and "
      "`tests/scenario/test_two_disruptions.py`.")
    A("")
    A("## 4 · Runbook")
    A("")
    A("```bash")
    A("pip install -r requirements.txt")
    A("python -m uvicorn main:app --reload --port 8000   # API")
    A("cd frontend && npm install && npm run dev          # dashboard :5173")
    A("python tools/report.py --demo                      # regenerate this evidence")
    A("python -m pytest tests -q                          # 18 checks")
    A("docker compose up                                  # full stack: Postgres + API + dashboard")
    A("```")
    A("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="reset the world and replay the two-disruption demo before reporting")
    args = ap.parse_args()

    store = EventStore()
    runs = None
    steps = []
    baseline = None
    if args.demo:
        captured = demo_payload(store)
        runs, steps = captured["runs"], captured["steps"]
        baseline = captured["baseline"]

    packet = collect(store, runs)
    if steps:
        packet["steps"] = steps
    if baseline:
        packet["baseline"] = baseline

    json_path = write_json(packet)
    md_path = write_md(packet)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"event_count={packet['event_count']} day={packet['sim_day']} "
          f"at_risk={packet['kpis']['at_risk_orders']}")

    final = packet["state"]["kpis"]
    print(f"final committed cost={final['total_cost']} carbon={final['total_carbon']} "
          f"(caps {final['budget_cap']}/{final['carbon_cap']})")


if __name__ == "__main__":
    main()