"""Deterministic cost / carbon / ETA calculators for candidate plans.

All functions are pure: they take a plan dict plus a read-only projection
and return a numeric value. No mutation.
"""
from __future__ import annotations

from typing import Any

from config import OBJ_WEIGHT_COST, OBJ_WEIGHT_TIME, OBJ_WEIGHT_CARBON
from simworld import projections


def candidate_cost(candidate: dict[str, Any], state: dict[str, Any]) -> float:
    """Total monetary cost: source price + route cost, per unit × qty."""
    route = state["routes"][candidate["route_id"]]
    qty = candidate["qty"]
    base = route["unit_cost"]
    if candidate["source_kind"] == "purchase":
        vendor = state["vendors"][candidate["source_id"]]
        base += vendor["unit_cost"][candidate["sku"]]
    return round(qty * base, 2)


def candidate_carbon(candidate: dict[str, Any], state: dict[str, Any]) -> float:
    route = state["routes"][candidate["route_id"]]
    return round(candidate["qty"] * route["unit_carbon"], 2)


def candidate_eta(candidate: dict[str, Any], current_day: int) -> int:
    transit = candidate.get("transit_days") or (candidate.get("route_info") or {}).get("transit_days", 999)
    return current_day + transit


def candidate_is_valid(candidate: dict[str, Any], state: dict[str, Any]) -> str | None:
    """Return reason string if the candidate violates a hard constraint, else None."""
    route = state["routes"].get(candidate["route_id"])
    if not route:
        return "route not found"
    if route["status"] != "open":
        return "route closed"
    if candidate["source_kind"] == "purchase":
        vendor = state["vendors"].get(candidate["source_id"])
        if not vendor:
            return "vendor not found"
        used = sum(vendor.get("capacity_used", {}).values())
        if vendor.get("capacity", 0) - used < candidate["qty"]:
            return "vendor capacity exhausted"
    elif candidate["source_kind"] == "allocate":
        wh = state["inventory"].get(candidate["source_id"], {})
        if wh.get(candidate["sku"], 0) < candidate["qty"]:
            return "insufficient warehouse stock"
    return None


def candidate_score(candidate: dict[str, Any], state: dict[str, Any], current_day: int) -> float:
    """Weighted objective: lower is better.

    Uses the same weight scheme the solver uses for ranking.
    Penalty for deadline overrun is baked in.
    """
    cost = candidate_cost(candidate, state)
    carbon = candidate_carbon(candidate, state)
    route = state["routes"][candidate["route_id"]]
    eta = candidate_eta({"transit_days": route["transit_days"]}, current_day)
    deadline = candidate["deadline"]
    lateness = max(0, eta - deadline)
    return (OBJ_WEIGHT_COST * cost
            + OBJ_WEIGHT_TIME * lateness * candidate["qty"]
            + OBJ_WEIGHT_CARBON * carbon)