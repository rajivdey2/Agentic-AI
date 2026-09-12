"""execute: issue the derived commands — every command emits exactly one event."""
from __future__ import annotations

from agent.tools import (
    allocate_inventory,
    cancel_shipment,
    place_order,
    reroute_shipment,
)
from agent.state import AgentState


def execute(state: AgentState) -> AgentState:
    actions = state.get("actions", [])
    executed = []
    for action in actions:
        kind = action["type"]
        params = action["params"]
        if kind == "cancel_shipment":
            ev = cancel_shipment(params["shipment_id"])
        elif kind == "reroute_shipment":
            ev = reroute_shipment(params["shipment_id"], params["route_id"])
        elif kind == "place_order":
            ev = place_order(params["order_id"], params["vendor_id"], params["qty"],
                             params["route_id"], reason=params.get("reason", ""))
        elif kind == "allocate_inventory":
            ev = allocate_inventory(params["order_id"], params["warehouse_id"], params["qty"],
                                    params["route_id"], reason=params.get("reason", ""))
        else:
            continue
        executed.append({"action": kind, "params": params, "event": ev})

    state["executed"] = state.get("executed", []) + executed
    state["status"] = "execute"
    state["message"] = f"Executed {len(executed)} command(s)"
    state["trace"] = state.get("trace", []) + [{
        "step": "execute",
        "day": state.get("day"),
        "summary": state["message"],
        "events": [ev["event"]["type"] for ev in executed],
    }]
    return state