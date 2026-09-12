"""Build candidate fulfillment plans for at-risk orders.

For each at-risk order the agent generates a bounded set of alternative plans:

  * one warehouse allocation per warehouse that can fully cover the need
  * one vendor purchase per vendor that can deliver to the destination
  * one route reroute per in-transit shipment that can still beat its deadline
    on a faster open route

Plans carry the *delta* vs current state (cancel list + resulting cost/carbon)
so the solver's budget/carbon constraints stay correct when an old plan is
replaced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import CANDIDATE_CAP
from optimizer.calculators import (
    candidate_carbon,
    candidate_cost,
    candidate_eta,
    candidate_is_valid,
    candidate_score,
)


@dataclass
class CandidatePlan:
    id: str
    order_id: str
    sku: str
    qty: int
    dest: str
    deadline: int
    source_kind: str           # "allocate" | "purchase" | "reroute"
    source_id: str             # warehouse_id | vendor_id | shipment_id
    source_location: str
    route_id: str
    action: str = "place_order_or_allocate"
    cancel_shipment_ids: list = field(default_factory=list)
    route_info: dict = field(default_factory=dict)
    total_cost: float = 0.0        # cost of this plan itself
    total_carbon: float = 0.0
    delta_cost: float = 0.0        # total_cost - cost of cancelled plans
    delta_carbon: float = 0.0
    eta: int = 0
    score: float = 0.0
    validity: str | None = None

    def asdict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "sku": self.sku,
            "qty": self.qty,
            "dest": self.dest,
            "deadline": self.deadline,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_location": self.source_location,
            "route_id": self.route_id,
            "action": self.action,
            "cancel_shipment_ids": list(self.cancel_shipment_ids),
            "route_info": dict(self.route_info),
            "total_cost": self.total_cost,
            "total_carbon": self.total_carbon,
            "delta_cost": self.delta_cost,
            "delta_carbon": self.delta_carbon,
            "eta": self.eta,
            "score": self.score,
            "validity": self.validity,
        }


def _best_routes(origin: str, dest: str, routes: dict[str, dict]) -> list[dict]:
    """Open routes from origin→dest, sorted by transit_days (fastest first)."""
    return sorted(
        [r for r in routes.values()
         if r["origin"] == origin and r["dest"] == dest and r["status"] == "open"],
        key=lambda r: r["transit_days"],
    )


def _order_context(order_id: str, state: dict) -> tuple[list[str], float, float]:
    """(cancel_shipment_ids, refunded_cost, refunded_carbon) for an at-risk order.

    Replaces any in-transit/lost shipments that can no longer make the deadline;
    on-time plans are kept and the new plan simply adds coverage.

    Only *in-transit* cancellations are refundable: a lost shipment is sunk cost
    (the projection keeps it committed), so it is cancelled to release capacity/
    stock but contributes nothing to the delta credit.
    """
    order = state["orders"][order_id]
    cancel_ids, ccost, ccarbon = [], 0.0, 0.0
    for s in state["shipments"].values():
        if s.get("order_id") != order_id or s["status"] not in ("in_transit", "lost"):
            continue
        if s["status"] == "lost" or s["eta"] > order["deadline"]:
            cancel_ids.append(s["id"])
            if s["status"] == "in_transit":
                ccost += s["cost"]
                ccarbon += s["carbon"]
    return cancel_ids, ccost, ccarbon


def _needed_qty(order_id: str, ro: dict, state: dict, cancel_ids: list[str]) -> int:
    order = state["orders"][order_id]
    covered = sum(
        s["qty"] for s in state["shipments"].values()
        if s.get("order_id") == order_id and s["status"] in ("in_transit", "delivered")
    )
    # Only late-but-in-transit cancellations were part of `covered`; lost ones were not.
    cancelled_late_qty = sum(
        s["qty"] for s in state["shipments"].values()
        if s["id"] in cancel_ids and s["status"] == "in_transit"
    )
    return max(1, order["qty"] - (covered - cancelled_late_qty))


def _warehouse_candidates(
    order, qty, dest, deadline, state, current_day, excluded, cancel_ids, ccost, ccarbon
) -> list[CandidatePlan]:
    plans = []
    for wh_id, wh in state["warehouses"].items():
        stock = state["inventory"].get(wh_id, {}).get(order["sku"], 0)
        if stock < qty:
            continue  # partial coverage is not a plan (must fully cover the order)
        for route in _best_routes(wh["location"], dest, state["routes"]):
            pid = f"PLAN-{order['id']}-allocate-{wh_id}-{route['id']}"
            if pid in excluded:
                continue
            cost = candidate_cost({"route_id": route["id"], "qty": qty,
                                   "source_kind": "allocate", "source_id": wh_id}, state)
            carbon = candidate_carbon({"route_id": route["id"], "qty": qty}, state)
            eta = candidate_eta({"transit_days": route["transit_days"]}, current_day)
            cp = CandidatePlan(
                id=pid, order_id=order["id"], sku=order["sku"], qty=qty, dest=dest,
                deadline=deadline, source_kind="allocate", source_id=wh_id,
                source_location=wh["location"], route_id=route["id"],
                action="allocate", cancel_shipment_ids=cancel_ids, route_info=route,
                total_cost=cost, total_carbon=carbon,
                delta_cost=round(cost - ccost, 2), delta_carbon=round(carbon - ccarbon, 2),
                eta=eta, score=candidate_score({"qty": qty, "deadline": deadline,
                                                "route_id": route["id"],
                                                "source_kind": "allocate",
                                                "source_id": wh_id}, state, current_day),
            )
            cp.validity = candidate_is_valid(
                {"route_id": route["id"], "source_kind": "allocate", "source_id": wh_id,
                 "sku": order["sku"], "qty": qty}, state)
            plans.append(cp)
    return plans


def _vendor_candidates(
    order, qty, dest, deadline, state, current_day, excluded, cancel_ids, ccost, ccarbon
) -> list[CandidatePlan]:
    plans = []
    for vendor in state["vendors"].values():
        if vendor["unit_cost"].get(order["sku"]) is None:
            continue
        for route in _best_routes(vendor["location"], dest, state["routes"]):
            pid = f"PLAN-{order['id']}-purchase-{vendor['id']}-{route['id']}"
            if pid in excluded:
                continue
            cost = candidate_cost({"route_id": route["id"], "qty": qty, "sku": order["sku"],
                                   "source_kind": "purchase", "source_id": vendor["id"]}, state)
            carbon = candidate_carbon({"route_id": route["id"], "qty": qty}, state)
            eta = candidate_eta({"transit_days": route["transit_days"]}, current_day)
            cp = CandidatePlan(
                id=pid, order_id=order["id"], sku=order["sku"], qty=qty, dest=dest,
                deadline=deadline, source_kind="purchase", source_id=vendor["id"],
                source_location=vendor["location"], route_id=route["id"],
                action="place_order", cancel_shipment_ids=cancel_ids, route_info=route,
                total_cost=cost, total_carbon=carbon,
                delta_cost=round(cost - ccost, 2), delta_carbon=round(carbon - ccarbon, 2),
                eta=eta, score=candidate_score({"qty": qty, "deadline": deadline,
                                                "route_id": route["id"],
                                                "source_kind": "purchase",
                                                "source_id": vendor["id"],
                                                "sku": order["sku"]}, state, current_day),
            )
            cp.validity = candidate_is_valid(
                {"route_id": route["id"], "source_kind": "purchase", "source_id": vendor["id"],
                 "sku": order["sku"], "qty": qty}, state)
            plans.append(cp)
    return plans


def _reroute_candidates(
    order, state, current_day, excluded
) -> list[CandidatePlan]:
    """Faster alternative routes for an in-transit shipment that is running late."""
    plans = []
    for s in state["shipments"].values():
        if s.get("order_id") != order["id"] or s["status"] != "in_transit":
            continue
        origin, dest = s["origin"], s["dest"]
        for route in _best_routes(origin, dest, state["routes"]):
            if route["id"] == s["route_id"]:
                continue
            pid = f"PLAN-{order['id']}-reroute-{s['id']}-{route['id']}"
            if pid in excluded:
                continue
            new_cost = s["cost"]
            new_carbon = s["carbon"]
            if route["id"] != s["route_id"]:
                new_cost = round(s["qty"] * route["unit_cost"] + s["cost"] - s["qty"] * state["routes"][s["route_id"]]["unit_cost"], 2)
                new_carbon = round(s["qty"] * route["unit_carbon"], 2)
            eta = current_day + route["transit_days"]
            cp = CandidatePlan(
                id=pid, order_id=order["id"], sku=s["sku"], qty=s["qty"], dest=dest,
                deadline=order["deadline"], source_kind="reroute", source_id=s["id"],
                source_location=origin, route_id=route["id"], action="reroute",
                cancel_shipment_ids=[], route_info=route,
                total_cost=new_cost, total_carbon=new_carbon,
                delta_cost=round(new_cost - s["cost"], 2),
                delta_carbon=round(new_carbon - s["carbon"], 2),
                eta=eta, score=candidate_score({"qty": s["qty"], "deadline": order["deadline"],
                                                "route_id": route["id"],
                                                "source_kind": "reroute",
                                                "source_id": s["id"], "sku": s["sku"]},
                                               state, current_day),
            )
            plans.append(cp)
    return plans


def build_candidates(
    risk_orders: list[dict],
    state: dict,
    current_day: int,
    excluded_candidates: set[str] | None = None,
) -> list[CandidatePlan]:
    """Return up to CANDIDATE_CAP candidates across all at-risk orders, ranked by score."""
    excluded = excluded_candidates or set()
    all_plans: list[CandidatePlan] = []
    for ro in risk_orders:
        oid = ro["order_id"]
        order = state["orders"][oid]
        cancel_ids, ccost, ccarbon = _order_context(oid, state)
        qty = _needed_qty(oid, ro, state, cancel_ids)
        dest, deadline = order["dest"], order["deadline"]
        plans = (
            _warehouse_candidates(order, qty, dest, deadline, state, current_day,
                                  excluded, cancel_ids, ccost, ccarbon)
            + _vendor_candidates(order, qty, dest, deadline, state, current_day,
                                 excluded, cancel_ids, ccost, ccarbon)
        )
        # reroute only helps when an existing in-flight shipment itself runs late
        if any("exceeds deadline" in r for r in ro.get("reasons", [])):
            plans += _reroute_candidates(order, state, current_day, excluded)
        plans.sort(key=lambda p: p.score)
        all_plans.extend(plans)
    all_plans.sort(key=lambda p: p.score)
    return all_plans[:CANDIDATE_CAP]