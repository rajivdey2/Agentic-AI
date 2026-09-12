"""OR-Tools CP-SAT solver for candidate assignment with a greedy fallback.

Only a bounded candidate set (<= ~15 plans) ever reaches the solver, so it
runs in well under the configured time limit. Constraints:

  * exactly one plan per at-risk order
  * vendor capacity across all chosen purchases
  * warehouse stock across all chosen allocations
  * aggregate cost <= remaining budget
  * aggregate carbon <= remaining carbon

If the hard problem is infeasible, budget/carbon caps are relaxed with a large
penalty so the agent always has a feasible action to try, and the returned
`status` tells the caller which constraint had to give.
"""
from __future__ import annotations

from typing import Any, Optional

from config import (
    OBJ_WEIGHT_COST,
    OBJ_WEIGHT_TIME,
    OBJ_WEIGHT_CARBON,
    SOLVER_TIME_LIMIT_SECONDS,
)
from optimizer.candidates import CandidatePlan


def _scaled(v: float) -> int:
    return int(round(v * 100))


def _group_orders(candidates: list[CandidatePlan]) -> dict[str, list[CandidatePlan]]:
    by_order: dict[str, list[CandidatePlan]] = {}
    for c in candidates:
        by_order.setdefault(c.order_id, []).append(c)
    return by_order


def _constraints_meta(candidates: list[CandidatePlan], state: dict) -> dict:
    """Available budget/carbon and per-vendor/warehouse limits."""
    k = state["kpis"]
    remaining_budget = max(0.0, k["remaining_budget"])
    remaining_carbon = max(0.0, k["remaining_carbon"])
    vendor_caps: dict[str, int] = {}
    wh_stock: dict[tuple[str, str], int] = {}
    for c in candidates:
        if c.source_kind == "purchase":
            v = state["vendors"][c.source_id]
            used = sum(v.get("capacity_used", {}).values())
            cap = max(0, v["capacity"] - used)
            vendor_caps.setdefault(c.source_id, cap)
            vendor_caps[c.source_id] = min(vendor_caps[c.source_id], cap)
        elif c.source_kind == "allocate":
            stock = state["inventory"].get(c.source_id, {}).get(c.sku, 0)
            key = (c.source_id, c.sku)
            wh_stock[key] = stock
    return {
        "remaining_budget": remaining_budget,
        "remaining_carbon": remaining_carbon,
        "vendor_caps": vendor_caps,
        "wh_stock": wh_stock,
    }


def _solve_cp(candidates: list[CandidatePlan], state: dict, current_day: int) -> Optional[dict]:
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return None

    meta = _constraints_meta(candidates, state)
    by_order = _group_orders(candidates)
    orders = list(by_order.keys())

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i, _ in enumerate(candidates)]

    for order_id, plans in by_order.items():
        idxs = [i for i, c in enumerate(candidates) if c.order_id == order_id]
        model.AddExactlyOne(x[i] for i in idxs)

    for vendor_id, cap in meta["vendor_caps"].items():
        idxs = [i for i, c in enumerate(candidates)
                if c.source_kind == "purchase" and c.source_id == vendor_id]
        if idxs:
            model.Add(sum(x[i] * c.qty for i, c in zip(idxs, [candidates[i] for i in idxs])) <= cap)

    for (wh, sku), stock in meta["wh_stock"].items():
        idxs = [i for i, c in enumerate(candidates)
                if c.source_kind == "allocate" and c.source_id == wh and c.sku == sku]
        if idxs:
            model.Add(sum(x[i] * c.qty for i, c in zip(idxs, [candidates[i] for i in idxs])) <= stock)

    over_budget = model.NewIntVar(0, 10**9, "over_budget")
    over_carbon = model.NewIntVar(0, 10**9, "over_carbon")
    model.Add(sum(x[i] * _scaled(c.delta_cost) for i, c in enumerate(candidates))
              - over_budget <= _scaled(meta["remaining_budget"]))
    model.Add(sum(x[i] * _scaled(c.delta_carbon) for i, c in enumerate(candidates))
              - over_carbon <= _scaled(meta["remaining_carbon"]))

    penalty = 10**8
    model.Minimize(
        sum(x[i] * _scaled(c.score) for i, c in enumerate(candidates))
        + penalty * over_budget + penalty * over_carbon
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    selected = [candidates[i] for i in range(len(candidates)) if solver.Value(x[i]) == 1]
    solved_over_budget = solver.Value(over_budget) > 0
    solved_over_carbon = solver.Value(over_carbon) > 0

    status_name = "optimal"
    if solved_over_budget and solved_over_carbon:
        status_name = "relaxed_budget_and_carbon"
    elif solved_over_budget:
        status_name = "relaxed_budget"
    elif solved_over_carbon:
        status_name = "relaxed_carbon"
    return _result(selected, orders, status_name, candidates)


def _greedy_fallback(candidates: list[CandidatePlan], state: dict, current_day: int) -> dict:
    meta = _constraints_meta(candidates, state)
    orders_needed = _group_orders(candidates)
    selected: list[CandidatePlan] = []
    usage_vendor: dict[str, int] = {k: 0 for k in meta["vendor_caps"]}
    usage_wh: dict[tuple[str, str], int] = {k: 0 for k in meta["wh_stock"]}

    for order_id, plans in orders_needed.items():
        chosen = None
        for c in sorted(plans, key=lambda p: p.score):
            if c.validity:
                continue
            if c.source_kind == "purchase" and usage_vendor.get(c.source_id, 0) + c.qty > meta["vendor_caps"].get(c.source_id, 10**9):
                continue
            if c.source_kind == "allocate":
                key = (c.source_id, c.sku)
                if usage_wh.get(key, 0) + c.qty > meta["wh_stock"].get(key, 10**9):
                    continue
            chosen = c
            break
        if chosen:
            selected.append(chosen)
            if chosen.source_kind == "purchase":
                usage_vendor[chosen.source_id] += chosen.qty
            else:
                key = (chosen.source_id, chosen.sku)
                usage_wh[key] = usage_wh.get(key, 0) + chosen.qty

    picked_orders = {c.order_id for c in selected}
    unfulfilled = [o for o in orders_needed if o not in picked_orders]
    return {
        "selected": [c.asdict() for c in selected],
        "unfulfilled_orders": unfulfilled,
        "status": "fallback_greedy",
        "ranked": [c.asdict() for c in sorted(candidates, key=lambda p: p.score)],
        "excluded": [],
        "total_cost": round(sum(c.total_cost for c in selected), 2),
        "total_carbon": round(sum(c.total_carbon for c in selected), 2),
        "delta_cost": round(sum(c.delta_cost for c in selected), 2),
        "delta_carbon": round(sum(c.delta_carbon for c in selected), 2),
    }


def _result(selected: list[CandidatePlan], orders: list[str], status: str,
            all_candidates: list[CandidatePlan]) -> dict:
    picked = {c.order_id for c in selected}
    return {
        "selected": [c.asdict() for c in selected],
        "unfulfilled_orders": [o for o in orders if o not in picked],
        "status": status,
        "ranked": [c.asdict() for c in sorted(all_candidates, key=lambda p: p.score)],
        "excluded": [],
        "total_cost": round(sum(c.total_cost for c in selected), 2),
        "total_carbon": round(sum(c.total_carbon for c in selected), 2),
        "delta_cost": round(sum(c.delta_cost for c in selected), 2),
        "delta_carbon": round(sum(c.delta_carbon for c in selected), 2),
    }


def solve(candidates: list[CandidatePlan], state: dict, current_day: int) -> dict:
    """Pick the optimal set of plans for all at-risk orders.

    Feasibility is enforced *before* ranking: candidates whose validity check
    failed (closed route, insufficient stock or exhausted vendor capacity) are
    never offered to the solver and are reported under `excluded` so the audit
    trail shows *why* they were blocked.
    """
    valid = [c for c in candidates if not c.validity]
    excluded = [c.asdict() for c in candidates if c.validity]
    if not valid:
        all_orders = sorted({c.order_id for c in candidates})
        return {"selected": [], "unfulfilled_orders": all_orders,
                "status": "infeasible", "ranked": [],
                "excluded": excluded,
                "total_cost": 0, "total_carbon": 0,
                "delta_cost": 0, "delta_carbon": 0}
    result = _solve_cp(valid, state, current_day)
    if result is None:
        result = _greedy_fallback(valid, state, current_day)
    result["excluded"] = excluded
    return result