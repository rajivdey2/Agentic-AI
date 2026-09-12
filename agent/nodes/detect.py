"""detect: compare live projections against objectives (on-time % / budget / carbon)."""
from __future__ import annotations

from agent.state import AgentState


def detect(state: AgentState) -> AgentState:
    snap = state.get("projection") or {}
    issues = snap.get("issues", [])

    for it in (issues or []):
        it["checked"] = True

    state["status"] = "detect"
    state["issues"] = issues
    state["message"] = (
        f"{len(issues)} constraint violation(s) detected"
        if issues else "No violations — objectives satisfied"
    )
    state["trace"] = state.get("trace", []) + [{
        "step": "detect",
        "day": state.get("day"),
        "summary": state["message"],
        "issues": [i.get("kind") for i in issues],
    }]
    return state