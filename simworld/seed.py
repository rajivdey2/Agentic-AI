"""Baseline seed scenario.

A small but non-trivial supply network so the agent has real alternatives to
reason over: 4 warehouses, 5 vendors, a set of inter-city routes (ground + a
couple of premium fast/lower-carbon air options), 3 SKUs and 5 active orders.
The baseline is feasible: every order's in-flight plan meets its deadline and
the committed cost/carbon stay under caps.
"""
from __future__ import annotations

from typing import Any

CITIES = ["CHN", "BLR", "MUM", "DEL", "HYD"]

# (origin, dest, transit_days, unit_cost, unit_carbon, capacity, suffix)
ROUTES: list[tuple[str, str, int, float, float, int, str]] = [
    ("CHN", "BLR", 2, 5.0, 1.2, 1000, ""),
    ("CHN", "MUM", 4, 8.0, 2.0, 1000, ""),
    ("CHN", "DEL", 5, 10.0, 2.8, 800, ""),
    ("CHN", "HYD", 3, 6.5, 1.6, 600, ""),
    ("BLR", "CHN", 2, 5.0, 1.2, 800, ""),
    ("BLR", "MUM", 3, 7.0, 1.8, 900, ""),
    ("BLR", "DEL", 4, 9.0, 2.4, 900, ""),
    ("BLR", "HYD", 2, 4.5, 1.1, 700, ""),
    ("MUM", "CHN", 4, 8.0, 2.0, 800, ""),
    ("MUM", "BLR", 3, 7.0, 1.8, 900, ""),
    ("MUM", "DEL", 2, 6.0, 1.5, 1000, ""),
    ("MUM", "HYD", 2, 4.0, 1.0, 800, ""),
    ("DEL", "CHN", 5, 10.0, 2.8, 700, ""),
    ("DEL", "BLR", 4, 9.0, 2.4, 900, ""),
    ("DEL", "MUM", 2, 6.0, 1.5, 900, ""),
    ("DEL", "HYD", 3, 7.0, 1.8, 600, ""),
    ("HYD", "CHN", 3, 6.5, 1.6, 600, ""),
    ("HYD", "BLR", 2, 4.5, 1.1, 700, ""),
    ("HYD", "MUM", 2, 4.0, 1.0, 800, ""),
    ("HYD", "DEL", 3, 7.0, 1.8, 600, ""),
    # premium air options (fast, expensive, carbon-heavy) — for trade-off drama
    ("CHN", "DEL", 1, 38.0, 6.0, 300, "AIR"),
    ("CHN", "MUM", 1, 34.0, 5.5, 350, "AIR"),
    ("MUM", "DEL", 1, 30.0, 5.0, 350, "AIR"),
    ("BLR", "DEL", 1, 32.0, 5.2, 300, "AIR"),
    # same-city / last-mile legs (local vendor delivery)
    ("CHN", "CHN", 1, 1.5, 0.2, 2000, ""),
    ("BLR", "BLR", 1, 1.5, 0.2, 2000, ""),
    ("MUM", "MUM", 1, 1.5, 0.2, 2000, ""),
    ("DEL", "DEL", 1, 1.5, 0.2, 2000, ""),
    ("HYD", "HYD", 1, 1.5, 0.2, 2000, ""),
]

WAREHOUSES: list[dict[str, Any]] = [
    {"id": "WH-CHN", "name": "Chennai Central", "location": "CHN", "capacity": 2000},
    {"id": "WH-BLR", "name": "Bengaluru Hub", "location": "BLR", "capacity": 2000},
    {"id": "WH-MUM", "name": "Mumbai Port", "location": "MUM", "capacity": 1500},
    {"id": "WH-DEL", "name": "Delhi Cluster", "location": "DEL", "capacity": 1500},
]

SKUS: list[dict[str, Any]] = [
    {"id": "SKU-A", "name": "Precision Widget", "unit_weight": 1.0},
    {"id": "SKU-B", "name": "Power Gadget", "unit_weight": 2.5},
    {"id": "SKU-C", "name": "Smart Gizmo", "unit_weight": 0.8},
]

# unit cost per SKU, per-day capacity, reliability [0,1]
VENDORS: list[dict[str, Any]] = [
    {"id": "V-CHN", "name": "Chennai Supplies", "location": "CHN",
     "unit_cost": {"SKU-A": 8.0, "SKU-B": 15.0, "SKU-C": 6.0}, "capacity": 400, "reliability": 0.97},
    {"id": "V-BLR", "name": "Bengaluru Components", "location": "BLR",
     "unit_cost": {"SKU-A": 9.0, "SKU-B": 14.0, "SKU-C": 7.0}, "capacity": 500, "reliability": 0.98},
    {"id": "V-MUM", "name": "Mumbai Manufacturing", "location": "MUM",
     "unit_cost": {"SKU-A": 7.0, "SKU-B": 16.0, "SKU-C": 5.0}, "capacity": 450, "reliability": 0.99},
    {"id": "V-DEL", "name": "Delhi Distribution", "location": "DEL",
     "unit_cost": {"SKU-A": 10.0, "SKU-B": 17.0, "SKU-C": 8.0}, "capacity": 300, "reliability": 0.95},
    {"id": "V-HYD", "name": "Hyderabad Freight", "location": "HYD",
     "unit_cost": {"SKU-A": 12.0, "SKU-B": 20.0, "SKU-C": 10.0}, "capacity": 250, "reliability": 0.99},
]

# Available (on-hand) inventory after the baseline allocations below are shipped.
INVENTORY: dict[str, dict[str, int]] = {
    "WH-CHN": {"SKU-A": 180, "SKU-B": 40, "SKU-C": 250},
    "WH-BLR": {"SKU-A": 60, "SKU-B": 200, "SKU-C": 100},
    "WH-MUM": {"SKU-A": 100, "SKU-B": 80, "SKU-C": 60},
    "WH-DEL": {"SKU-A": 60, "SKU-B": 30, "SKU-C": 20},
}

ORDERS: list[dict[str, Any]] = [
    {"id": "O-1", "sku": "SKU-A", "qty": 120, "dest": "DEL", "deadline": 8,
     "customer": "NorthMart"},
    {"id": "O-2", "sku": "SKU-B", "qty": 60, "dest": "BLR", "deadline": 6,
     "customer": "TechHub"},
    {"id": "O-3", "sku": "SKU-C", "qty": 200, "dest": "MUM", "deadline": 10,
     "customer": "GadgetRetail"},
    {"id": "O-4", "sku": "SKU-A", "qty": 90, "dest": "CHN", "deadline": 7,
     "customer": "ChennaiMall"},
    {"id": "O-5", "sku": "SKU-B", "qty": 40, "dest": "MUM", "deadline": 9,
     "customer": "UrbanBuy"},
]

# In-flight shipments that implement the baseline plans.
# cost/carbon are derived from route + vendor, not stored.
SHIPMENTS: list[dict[str, Any]] = [
    {"id": "S-1", "sku": "SKU-A", "qty": 120, "origin": "WH-CHN", "dest": "DEL",
     "route_id": "R_CHN_DEL", "eta": 5, "status": "in_transit",
     "order_id": "O-1", "kind": "allocate", "source_warehouse": "WH-CHN"},
    {"id": "S-2", "sku": "SKU-B", "qty": 60, "origin": "MUM", "dest": "BLR",
     "route_id": "R_MUM_BLR", "eta": 3, "status": "in_transit",
     "order_id": "O-2", "kind": "purchase", "vendor_id": "V-MUM"},
    {"id": "S-3", "sku": "SKU-C", "qty": 200, "origin": "CHN", "dest": "MUM",
     "route_id": "R_CHN_MUM", "eta": 4, "status": "in_transit",
     "order_id": "O-3", "kind": "purchase", "vendor_id": "V-CHN"},
    {"id": "S-4", "sku": "SKU-A", "qty": 90, "origin": "WH-BLR", "dest": "CHN",
     "route_id": "R_BLR_CHN", "eta": 2, "status": "in_transit",
     "order_id": "O-4", "kind": "allocate", "source_warehouse": "WH-BLR"},
    {"id": "S-5", "sku": "SKU-B", "qty": 40, "origin": "DEL", "dest": "MUM",
     "route_id": "R_DEL_MUM", "eta": 2, "status": "in_transit",
     "order_id": "O-5", "kind": "purchase", "vendor_id": "V-DEL"},
]

OBJECTIVES = {
    "on_time_target": 0.95,
    "budget_cap": 9000.0,
    "carbon_cap": 1600.0,
}


def route_id(origin: str, dest: str) -> str:
    return f"R_{origin}_{dest}"


def seed_payload() -> dict[str, Any]:
    return {
        "warehouses": WAREHOUSES,
        "skus": SKUS,
        "vendors": VENDORS,
        "routes": [
            {
                "id": route_id(o, d) + ("_AIR" if suffix else ""),
                "origin": o,
                "dest": d,
                "transit_days": td,
                "unit_cost": uc,
                "unit_carbon": cc,
                "capacity": cap,
                "status": "open",
            }
            for o, d, td, uc, cc, cap, suffix in ROUTES
        ],
        "inventory": INVENTORY,
        "orders": ORDERS,
        "shipments": SHIPMENTS,
        "objectives": OBJECTIVES,
    }