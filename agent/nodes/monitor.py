"""monitor: read the live projection and record the audit step."""
from __future__ import annotations

from agent.context import ctx
from agent.state import AgentState


def monitor(state: AgentState) -> AgentState:
    snap = ctx.snapshot()
    from simworld.events import sim_day
    state["projection"] = snap
    state["day"] = sim_day()
    state["status"] = "monitor"
    state["issues"] = snap.get("issues", [])
    state["risk_orders"] = snap.get("risk_orders", [])
    state["trace"] = state.get("trace", []) + [{
        "step": "monitor",
        "day": state["day"],
        "summary": f"Monitored {len(snap['orders'])} orders, {len(snap['shipments'])} shipments.",
    }]
    return state