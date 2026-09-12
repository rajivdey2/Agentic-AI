"""Projections: derive all current-state views by replaying the event log.

Nothing here mutates stored data — `rebuild(events, day)` returns a fresh,
complete state snapshot. Shipments whose ETA has passed *settle* (arrive at
their destination) as a derived step for a given day D, so replay is fully
deterministic for a fixed D.
"""
from __future__ import annotations

from typing import Any

SHIPMENT_STATUSES = ("in_transit", "delivered", "lost", "cancelled")


def _build(events: list[dict]) -> dict[str, Any]:
    st = {
        "warehouses": {},
        "skus": {},
        "vendors": {},
        "routes": {},
        "inventory": {},
        "orders": {},
        "shipments": {},
        "objectives": {"on_time_target": 0.95, "budget_cap": float("inf"), "carbon_cap": float("inf")},
        "counter": 0,
    }

    def _route(rid: str) -> dict:
        return st["routes"][rid]

    for ev in events:
        t, p = ev["type"], ev["payload"]
        if t == "seed":
            for w in p["warehouses"]:
                st["warehouses"][w["id"]] = dict(w)
                st["inventory"][w["id"]] = dict(p["inventory"].get(w["id"], {}))
            for s in p["skus"]:
                st["skus"][s["id"]] = dict(s)
            for v in p["vendors"]:
                vv = dict(v)
                vv["capacity_used"] = {}
                st["vendors"][v["id"]] = vv
            for r in p["routes"]:
                st["routes"][r["id"]] = dict(r)
            for o in p["orders"]:
                oo = dict(o)
                oo["status"] = "open"
                oo["delivered_qty"] = 0
                oo["shortfall"] = oo["qty"]
                oo["fulfilled_at"] = None
                st["orders"][o["id"]] = oo
            for s in p["shipments"]:
                ss = dict(s)
                ss["original_route_id"] = ss.get("route_id")
                ss["delay_days"] = 0
                ss["reroute_log"] = []
                ss["cost"] = 0.0
                ss["carbon"] = 0.0
                st["shipments"][ss["id"]] = ss
            st["objectives"].update(p.get("objectives", {}))
        elif t == "vendor_capacity_drop":
            v = st["vendors"][p["vendor_id"]]
            v["capacity"] = p["new_capacity"]
        elif t == "shipment_delay":
            s = st["shipments"].get(p["shipment_id"])
            if s and s["status"] == "in_transit":
                delay = p.get("delay_days", 1)
                s["eta"] += delay
                s["delay_days"] += delay
                s["delay_log"] = s.get("delay_log", []) + [{"day": ev["day"], "delay": delay}]
        elif t == "shipment_cancel":
            s = st["shipments"].get(p["shipment_id"])
            if s and s["status"] in ("in_transit", "lost"):
                s["status"] = "cancelled"
                s["cancelled_day"] = ev["day"]
                if s["kind"] == "allocate":
                    # refund stock only if nothing ever shipped
                    if s.get("_cancelled_from") != "lost":
                        _adjust_inventory(st, s["source_warehouse"], s["sku"], +s["qty"])
                if s["kind"] == "purchase" and s.get("vendor_id"):
                    _release_vendor_capacity(st, s["vendor_id"], s["sku"], s["qty"] * -1)
        elif t == "shipment_loss":
            s = st["shipments"].get(p["shipment_id"])
            if s and s["status"] == "in_transit":
                s["status"] = "lost"
                s["lost_day"] = ev["day"]
                s["_cancelled_from"] = "lost"
        elif t == "route_closed":
            if p["route_id"] in st["routes"]:
                _route(p["route_id"])["status"] = "closed"
        elif t == "demand_spike":
            o = st["orders"][p["order_id"]]
            o["qty"] = p["new_qty"]
            if p.get("new_deadline"):
                o["deadline"] = p["new_deadline"]
        elif t == "cap_change":
            st["objectives"].update(
                {k: v for k, v in p.items() if k in ("budget_cap", "carbon_cap", "on_time_target")}
            )
        elif t == "reroute_shipment":
            s = st["shipments"].get(p["shipment_id"])
            if s and s["status"] == "in_transit":
                new_route = _route(p["route_id"])
                s["reroute_log"].append({"day": ev["day"], "route_id": p["route_id"],
                                         "from": s["route_id"]})
                s["route_id"] = p["route_id"]
                s["eta"] = ev["day"] + new_route["transit_days"]
        elif t == "place_order":
            o = st["orders"][p["order_id"]]
            v = st["vendors"][p["vendor_id"]]
            route = _route(p["route_id"])
            sid = p.get("shipment_id") or f"S-PO-{st['counter']}"
            st["counter"] += 1
            cost = p["qty"] * (v["unit_cost"][o["sku"]] + route["unit_cost"])
            carbon = p["qty"] * route["unit_carbon"]
            if s := st["shipments"].get(sid):
                s.update({
                    "sku": o["sku"], "qty": p["qty"], "origin": v["location"],
                    "dest": o["dest"], "route_id": p["route_id"],
                    "eta": ev["day"] + route["transit_days"], "status": "in_transit",
                    "order_id": o["id"], "kind": "purchase", "vendor_id": v["id"],
                    "source_warehouse": None, "cost": 0.0, "carbon": 0.0,
                    "reroute_log": [], "delay_days": 0,
                })
            else:
                st["shipments"][sid] = {
                    "id": sid, "sku": o["sku"], "qty": p["qty"], "origin": v["location"],
                    "dest": o["dest"], "route_id": p["route_id"], "original_route_id": p["route_id"],
                    "eta": ev["day"] + route["transit_days"], "status": "in_transit",
                    "order_id": o["id"], "kind": "purchase", "vendor_id": v["id"],
                    "source_warehouse": None, "cost": 0.0, "carbon": 0.0,
                    "reroute_log": [], "delay_days": 0, "created_at_day": ev["day"],
                }
            v["capacity_used"].setdefault(o["sku"], 0)
            v["capacity_used"][o["sku"]] += p["qty"]
        elif t == "allocate_inventory":
            o = st["orders"][p["order_id"]]
            route = _route(p["route_id"])
            sid = p.get("shipment_id") or f"S-AL-{st['counter']}"
            st["counter"] += 1
            eta = ev["day"] + route["transit_days"]
            if s := st["shipments"].get(sid):
                s.update({
                    "sku": o["sku"], "qty": p["qty"], "origin": p["warehouse_id"],
                    "dest": o["dest"], "route_id": p["route_id"], "eta": eta,
                    "status": "in_transit", "order_id": o["id"], "kind": "allocate",
                    "source_warehouse": p["warehouse_id"], "vendor_id": None,
                    "cost": 0.0, "carbon": 0.0, "reroute_log": [], "delay_days": 0,
                })
            else:
                st["shipments"][sid] = {
                    "id": sid, "sku": o["sku"], "qty": p["qty"], "origin": p["warehouse_id"],
                    "dest": o["dest"], "route_id": p["route_id"], "original_route_id": p["route_id"],
                    "eta": eta, "status": "in_transit", "order_id": o["id"], "kind": "allocate",
                    "source_warehouse": p["warehouse_id"], "vendor_id": None,
                    "cost": 0.0, "carbon": 0.0, "reroute_log": [], "delay_days": 0,
                    "created_at_day": ev["day"],
                }
            st["inventory"][p["warehouse_id"]][o["sku"]] -= p["qty"]
        elif t == "transfer_stock":
            route = _route(p["route_id"])
            sid = p.get("shipment_id") or f"S-TR-{st['counter']}"
            st["counter"] += 1
            st["shipments"][sid] = {
                "id": sid, "sku": p["sku"], "qty": p["qty"], "origin": p["from_wh"],
                "dest": p["to_wh"], "route_id": p["route_id"], "original_route_id": p["route_id"],
                "eta": ev["day"] + route["transit_days"], "status": "in_transit",
                "order_id": None, "kind": "transfer", "vendor_id": None,
                "source_warehouse": p["from_wh"], "cost": 0.0, "carbon": 0.0,
                "reroute_log": [], "delay_days": 0, "created_at_day": ev["day"],
            }
            st["inventory"][p["from_wh"]][p["sku"]] -= p["qty"]

    # derive shipment cost/carbon from current route + vendor pricing
    for s in st["shipments"].values():
        if s["status"] == "cancelled":
            # lost-then-cancelled shipments are sunk cost; cancelled in-transit are refunded
            if s.get("_cancelled_from") == "lost":
                _derive_shipment_ledger(st, s)
            else:
                s["cost"], s["carbon"] = 0.0, 0.0
            continue
        _derive_shipment_ledger(st, s)
    return st


def _derive_shipment_ledger(st: dict, s: dict) -> None:
    route = st["routes"][s["route_id"]]
    s["carbon"] = round(s["qty"] * route["unit_carbon"], 2)
    base = route["unit_cost"]
    if s["kind"] == "purchase" and s.get("vendor_id"):
        vendor = st["vendors"][s["vendor_id"]]
        sku = s["sku"]
        base += vendor["unit_cost"].get(sku, 0)
    s["cost"] = round(s["qty"] * base, 2)


def _adjust_inventory(st: dict, wh: str, sku: str, delta: int) -> None:
    st["inventory"].setdefault(wh, {}).setdefault(sku, 0)
    st["inventory"][wh][sku] += delta


def _release_vendor_capacity(st: dict, vendor_id: str, sku: str, qty: int) -> None:
    v = st["vendors"][vendor_id]
    v["capacity_used"].setdefault(sku, 0)
    v["capacity_used"][sku] = max(0, v["capacity_used"][sku] + qty)


def settle(st: dict, day: int) -> None:
    """Deliver all in-transit shipments whose ETA has passed by `day`."""
    for s in sorted(st["shipments"].values(), key=lambda x: x["eta"]):
        if s["status"] == "in_transit" and s["eta"] <= day:
            s["status"] = "delivered"
            s["delivered_day"] = s["eta"]
            if s["kind"] == "transfer":
                _adjust_inventory(st, s["dest"], s["sku"], s["qty"])
            if s["order_id"]:
                o = st["orders"][s["order_id"]]
                o["delivered_qty"] += s["qty"]
                if o["delivered_qty"] >= o["qty"] and o["status"] == "open":
                    o["status"] = "fulfilled"
                    o["fulfilled_at"] = s["eta"]


def _order_coverage(st: dict, order_id: str) -> dict:
    """Sum of non-cancelled/non-lost shipment qty plus delivered qty for an order."""
    o = st["orders"][order_id]
    active = []
    for s in st["shipments"].values():
        if s.get("order_id") == order_id and s["status"] in ("in_transit", "delivered"):
            active.append(s)
    covered = sum(s["qty"] for s in active)
    earliest = min((s["eta"] for s in active if s["status"] == "in_transit"), default=None)
    return {"covered": covered, "shortfall": o["qty"] - covered, "earliest_eta": earliest, "shipments": active}


def finalize_kpis(st: dict, day: int) -> None:
    settle(st, day)
    committed = [
        s for s in st["shipments"].values()
        if s["status"] != "cancelled" or s.get("_cancelled_from") == "lost"
    ]
    total_cost = round(sum(s["cost"] for s in committed), 2)
    total_carbon = round(sum(s["carbon"] for s in committed), 2)
    fulfilled = [o for o in st["orders"].values() if o["status"] == "fulfilled"]
    on_time = sum(
        1 for o in fulfilled if o["fulfilled_at"] is not None and o["fulfilled_at"] <= o["deadline"]
    )
    st["kpis"] = {
        "total_cost": total_cost,
        "total_carbon": total_carbon,
        "on_time_delivered": on_time,
        "orders_fulfilled": len(fulfilled),
        "on_time_rate": round(on_time / len(fulfilled), 4) if fulfilled else 1.0,
        "budget_cap": st["objectives"]["budget_cap"],
        "carbon_cap": st["objectives"]["carbon_cap"],
        "remaining_budget": round(st["objectives"]["budget_cap"] - total_cost, 2),
        "remaining_carbon": round(st["objectives"]["carbon_cap"] - total_carbon, 2),
        "open_orders": sum(1 for o in st["orders"].values() if o["status"] == "open"),
        "at_risk_orders": len(_at_risk(st)),
    }
    for o in st["orders"].values():
        cov = _order_coverage(st, o["id"])
        o["shortfall"] = max(0, cov["shortfall"])


def _at_risk(st: dict) -> list[dict]:
    """Orders that will violate the on-time objective unless replanned."""
    risks: list[dict] = []
    for o in st["orders"].values():
        if o["status"] != "open":
            continue
        cov = _order_coverage(st, o["id"])
        reasons = []
        if cov["shortfall"] > 0:
            reasons.append(f"supply shortfall {cov['shortfall']} units")
        if cov["earliest_eta"] is None or cov["earliest_eta"] > o["deadline"]:
            reasons.append(f"latest ETA {cov['earliest_eta']} exceeds deadline {o['deadline']}")
        if reasons:
            risks.append({
                "order_id": o["id"],
                "sku": o["sku"],
                "qty": cov["shortfall"] or o["qty"],
                "shortfall": max(0, cov["shortfall"]),
                "dest": o["dest"],
                "deadline": o["deadline"],
                "earliest_eta": cov["earliest_eta"],
                "covered": cov["covered"],
                "reasons": reasons,
            })
    return risks


def rebuild(events: list[dict], day: int) -> dict[str, Any]:
    """Rebuild full projection from the event log, settled at `day`."""
    st = _build(events)
    finalize_kpis(st, day)
    st["day"] = day
    st["risk_orders"] = _at_risk(st)
    return st


def issues(st: dict, day: int) -> list[dict]:
    """Real constraint check used by detect/verify: returns list of violations."""
    out: list[dict] = []
    for r in _at_risk(st):
        out.append({"kind": "deadline_risk", **r})
    k = st["kpis"]
    if k["total_cost"] > k["budget_cap"]:
        out.append({"kind": "budget_cap",
                    "detail": f"cost {k['total_cost']} exceeds cap {k['budget_cap']}"})
    if k["total_carbon"] > k["carbon_cap"]:
        out.append({"kind": "carbon_cap",
                    "detail": f"carbon {k['total_carbon']} exceeds cap {k['carbon_cap']}"})
    fulfilled = k["orders_fulfilled"]
    if fulfilled and k["on_time_rate"] < st["objectives"]["on_time_target"]:
        out.append({"kind": "on_time_target",
                    "detail": f"on-time {k['on_time_rate']:.0%} below target "
                              f"{st['objectives']['on_time_target']:.0%}"})
    return out