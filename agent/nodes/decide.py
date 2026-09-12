"""decide: turn the optimal solver assignment into concrete actions + justification.

This is where the LLM earns its place: given the ranked candidates and the
solver's selection, it writes a short human-readable justification of the
chosen trade-off (cost / delivery-time / carbon). Deterministic fallback keeps
the demo moving if the API is slow or unavailable.
"""
from __future__ import annotations

from agent.context import ctx
from agent.state import AgentState


def decide(state: AgentState) -> AgentState:
    solver_result = state.get("solver", {})
    ranked = solver_result.get("ranked", [])
    selected = solver_result.get("selected", [])
    primary = selected[0] if selected else (ranked[0] if ranked else None)

    default = ctx.llm.decide(
        {"ranked_candidates": ranked, "selected": selected},
        {
            "choice": primary["id"] if primary else None,
            "justification": (
                "Deterministic fallback: the optimizer selected the plan with the "
                "lowest weighted cost/time/carbon trade-off while respecting "
                "capacity and constraint caps."
            ),
            "provider": "deterministic-fallback",
            "model": "none",
            "latency_ms": 0,
        },
    )

    # The optimizer already picked the assignment; the LLM only narrates it.
    # `choice` always mirrors the executed selection so the trace is truthful.
    decision = {
        "choice": primary["id"] if primary else default["choice"],
        "justification": default["justification"],
        "provider": default["provider"],
        "model": default.get("model"),
        "latency_ms": default.get("latency_ms", 0),
        "summary": default.get("summary", ""),
        "selected": selected,
    }
    if default.get("llm_error"):
        decision["llm_error"] = default["llm_error"]

    # Map each selected candidate to an executable command list.
    actions = []
    for plan in selected:
        if plan["source_kind"] == "reroute":
            actions.append({
                "type": "reroute_shipment",
                "params": {"shipment_id": plan["source_id"], "route_id": plan["route_id"]},
                "plan": plan,
            })
        else:
            command = {
                "type": "place_order" if plan["source_kind"] == "purchase" else "allocate_inventory",
                "params": {
                    "order_id": plan["order_id"],
                    "qty": plan["qty"],
                    "route_id": plan["route_id"],
                    "reason": default["justification"][:140],
                },
            }
            if plan["source_kind"] == "purchase":
                command["params"]["vendor_id"] = plan["source_id"]
            else:
                command["params"]["warehouse_id"] = plan["source_id"]
            for cid in plan["cancel_shipment_ids"]:
                actions.append({"type": "cancel_shipment", "params": {"shipment_id": cid}, "plan": plan})
            actions.append(command)

    state["decision"] = decision
    state["actions"] = actions
    state["status"] = "decide"
    state["message"] = f"Decision: {decision['choice'] or 'none'} ({decision['provider']})"
    state["trace"] = state.get("trace", []) + [{
        "step": "decide",
        "day": state.get("day"),
        "summary": state["message"],
        "choice": decision["choice"],
        "justification": decision["justification"][:400],
        "actions": [a["type"] for a in actions],
    }]
    return state