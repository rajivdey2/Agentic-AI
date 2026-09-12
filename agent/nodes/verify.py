"""verify: re-read the projection and re-run the real constraint check.

A failed verification loops back to `retrieve` with the failed candidates
excluded — this is the literal "replan when the chosen alternative becomes
unavailable" requirement. After `max_verify_attempts` failures the graph
routes to `escalate_to_human`.
"""
from __future__ import annotations

from agent.context import ctx
from agent.state import AgentState


def verify(state: AgentState) -> AgentState:
    snap = ctx.snapshot()
    issues = snap.get("issues", [])
    passed = len(issues) == 0

    attempt = state.get("replan_count", 0) + 1
    state["replan_count"] = attempt

    failed_plans = [p["id"] for p in state.get("solver", {}).get("selected", [])]
    if not passed:
        state["excluded"] = sorted(set(state.get("excluded", [])) | set(failed_plans))

    state["verification"] = {
        "passed": passed,
        "attempt": attempt,
        "issues_after": issues,
        "kpis": {
            "total_cost": snap["kpis"]["total_cost"],
            "total_carbon": snap["kpis"]["total_carbon"],
            "remaining_budget": snap["kpis"]["remaining_budget"],
            "remaining_carbon": snap["kpis"]["remaining_carbon"],
            "at_risk_orders": snap["kpis"]["at_risk_orders"],
        },
    }
    state["status"] = "verify"
    state["message"] = (
        "Constraints satisfied ✓" if passed
        else f"Verification failed ({attempt}/{ctx.max_verify_attempts})"
    )
    state["trace"] = state.get("trace", []) + [{
        "step": "verify",
        "day": state.get("day"),
        "passed": passed,
        "summary": state["message"],
        "issues_after": [i.get("kind") for i in issues],
    }]
    return state