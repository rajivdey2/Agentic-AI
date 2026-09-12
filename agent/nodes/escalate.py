"""escalate: the system never pretends an unsolved problem is solved."""
from __future__ import annotations

from agent.state import AgentState


def escalate(state: AgentState) -> AgentState:
    state["status"] = "escalated"
    state["message"] = (
        "Escalating to human: could not reach a constraint-satisfying state "
        f"after {state.get('replan_count', 0)} replan attempt(s)."
    )
    state["trace"] = state.get("trace", []) + [{
        "step": "escalate_to_human",
        "day": state.get("day"),
        "summary": state["message"],
    }]
    return state