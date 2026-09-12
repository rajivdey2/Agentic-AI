"""optimize: run the OR-Tools assignment solver over the candidate set."""
from __future__ import annotations

from agent.context import ctx
from agent.state import AgentState
from optimizer.solvers import solve


def optimize(state: AgentState) -> AgentState:
    snap = state.get("projection") or {}
    current_day = snap.get("day", state.get("day", 0))

    candidate_objs = ctx._candidate_objs.get(state.get("run_id", "run-0"), [])
    solver = solve(candidate_objs, snap, current_day)
    state["solver"] = solver
    state["status"] = "optimize"
    state["message"] = f"Solver status: {solver['status']}; selected {len(solver['selected'])} plan(s)"
    state["trace"] = state.get("trace", []) + [{
        "step": "optimize",
        "day": state.get("day"),
        "summary": state["message"],
        "solver_status": solver["status"],
        "selected_ids": [p["id"] for p in solver["selected"]],
        "delta_cost": solver.get("delta_cost"),
        "delta_carbon": solver.get("delta_carbon"),
    }]
    return state