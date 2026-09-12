"""retrieve: gather alternative vendor/route/stock options for at-risk orders."""
from __future__ import annotations

from agent.context import ctx
from agent.state import AgentState
from optimizer.candidates import build_candidates


def retrieve(state: AgentState) -> AgentState:
    snap = state.get("projection") or {}
    risk = snap.get("risk_orders", []) or state.get("risk_orders", [])
    excluded = set(state.get("excluded", []))
    candidates = build_candidates(risk, snap, snap.get("day", state.get("day", 0)),
                                  excluded_candidates=excluded)
    state["run_id"] = state.get("run_id", "run-0")
    ctx._candidate_objs[state["run_id"]] = candidates
    state["candidates"] = [c.asdict() for c in candidates]
    state["status"] = "retrieve"
    state["message"] = f"Retrieved {len(state['candidates'])} candidate plan(s)"
    state["trace"] = state.get("trace", []) + [{
        "step": "retrieve",
        "day": state.get("day"),
        "summary": state["message"],
        "candidate_ids": [c["id"] for c in state["candidates"]],
        "at_risk": [r["order_id"] for r in risk],
    }]
    return state