"""Disruption injector: changes to the environment that force replanning.

Each disruption appends a domain event (so it is part of the audit trail) and
the agent reacts to the *projection* changes it causes. Includes a manual
"chaos" endpoint for the live demo so the required failure scenario can be
guaranteed to fire on cue, twice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from simworld.events import EventStore
from simworld import world

DISRUPTION_TYPES = ("vendor_capacity_drop", "shipment_delay", "shipment_loss",
                    "route_closed", "demand_spike", "cap_change")


@dataclass
class Disruption:
    type: str
    params: dict[str, Any]
    label: str = ""
    events: list[dict] = field(default_factory=list)

    def apply(self, store: EventStore | None = None) -> list[dict]:
        """Emit the disruption event(s); returns what was appended."""
        store = store or EventStore()
        if self.type == "vendor_capacity_drop":
            self.events.append(store.append(
                "vendor_capacity_drop",
                {"vendor_id": self.params["vendor_id"], "new_capacity": self.params["new_capacity"]},
            ))
        elif self.type == "shipment_delay":
            self.events.append(store.append(
                "shipment_delay",
                {"shipment_id": self.params["shipment_id"], "delay_days": self.params["delay_days"]},
            ))
        elif self.type == "shipment_loss":
            self.events.append(store.append(
                "shipment_loss", {"shipment_id": self.params["shipment_id"]},
            ))
        elif self.type == "route_closed":
            self.events.append(store.append(
                "route_closed", {"route_id": self.params["route_id"]},
            ))
        elif self.type == "demand_spike":
            self.events.append(store.append(
                "demand_spike",
                {"order_id": self.params["order_id"], "new_qty": self.params["new_qty"],
                 "new_deadline": self.params.get("new_deadline")},
            ))
        elif self.type == "cap_change":
            self.events.append(store.append(
                "cap_change", {k: v for k, v in self.params.items() if k in (
                    "budget_cap", "carbon_cap", "on_time_target")},
            ))
        else:
            raise ValueError(f"unknown disruption type: {self.type}")
        return self.events


def build_disruption(
    kind: str,
    params: dict[str, Any] | None = None,
    store: EventStore | None = None,
) -> Disruption:
    """Build a disruption, auto-choosing sensible demo targets when omitted."""
    params = dict(params or {})
    st = world.get_state(store or EventStore())

    if kind == "vendor_capacity_drop":
        params.setdefault("vendor_id", "V-CHN")
        params.setdefault("new_capacity", 50)
        label = (f"Vendor {params['vendor_id']} capacity cap dropped to "
                 f"{params['new_capacity']}/day")
    elif kind == "shipment_delay":
        default = next((s["id"] for s in st["shipments"].values()
                        if s["status"] == "in_transit"), "S-3")
        params.setdefault("shipment_id", default)
        params.setdefault("delay_days", 6)
        label = (f"Shipment {params['shipment_id']} delayed by {params['delay_days']} days")
    elif kind == "shipment_loss":
        default = next((s["id"] for s in st["shipments"].values()
                        if s["status"] == "in_transit"), "S-3")
        params.setdefault("shipment_id", default)
        label = f"Shipment {params['shipment_id']} lost in transit"
    elif kind == "route_closed":
        default = next((r["id"] for r in st["routes"].values() if r["status"] == "open"), "R_CHN_MUM")
        params.setdefault("route_id", default)
        label = f"Route {params['route_id']} closed"
    elif kind == "demand_spike":
        default = next((o["id"] for o in st["orders"].values() if o["status"] == "open"), "O-3")
        params.setdefault("order_id", default)
        params.setdefault("new_qty", 300)
        params.setdefault("new_deadline", 9)
        label = (f"Demand spike: order {params['order_id']} -> {params['new_qty']} units, "
                 f"deadline {params['new_deadline']}")
    elif kind == "cap_change":
        params.setdefault("carbon_cap", 1200.0)
        label = f"Carbon cap tightened to {params.get('carbon_cap')}"
    else:
        raise ValueError(f"unknown disruption type: {kind}")
    return Disruption(type=kind, params=params, label=label)