"""High-level commands: every action emits events through the append-only store.

These are the *only* way SimWorld state changes. Read-side views come from
projections (rebuild-from-log); write-side always routes through here.
"""
from __future__ import annotations

from typing import Any, Optional

from simworld import projections
from simworld.events import EventStore
from simworld.seed import seed_payload

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def ensure_seeded(store: EventStore | None = None) -> bool:
    """Append the seed event once; returns True if it was created."""
    store = store or EventStore()
    if store.store_empty():
        store.append("seed", seed_payload(), day=0)
        return True
    return False


# ---------------------------------------------------------------------------
# Read side
# ---------------------------------------------------------------------------


def get_state(store: EventStore | None = None, day: int | None = None) -> dict[str, Any]:
    from simworld.events import sim_day

    store = store or EventStore()
    events = store.events()
    current = sim_day() if day is None else day
    st = projections.rebuild(events, current)
    st["sim_day"] = current
    st["issues"] = projections.issues(st, current)
    st["event_count"] = len(events)
    return st


# ---------------------------------------------------------------------------
# Write side (agent + demo commands). Each returns the created event(s).
# ---------------------------------------------------------------------------

PLACE_ORDER_EVENT = "place_order"
ALLOCATE_EVENT = "allocate_inventory"
TRANSFER_EVENT = "transfer_stock"
REROUTE_EVENT = "reroute_shipment"
CANCEL_EVENT = "shipment_cancel"


def reroute_shipment(store: EventStore, shipment_id: str, route_id: str) -> dict:
    return store.append(REROUTE_EVENT, {"shipment_id": shipment_id, "route_id": route_id})


def cancel_shipment(store: EventStore, shipment_id: str) -> dict:
    return store.append(CANCEL_EVENT, {"shipment_id": shipment_id})


def place_order(
    store: EventStore,
    order_id: str,
    vendor_id: str,
    qty: int,
    route_id: str,
    reason: str = "",  # attached to the audit trail
) -> dict:
    return store.append(
        PLACE_ORDER_EVENT,
        {"order_id": order_id, "vendor_id": vendor_id, "qty": qty, "route_id": route_id,
         "reason": reason},
    )


def allocate_inventory(
    store: EventStore,
    order_id: str,
    warehouse_id: str,
    qty: int,
    route_id: str,
    reason: str = "",
) -> dict:
    return store.append(
        ALLOCATE_EVENT,
        {"order_id": order_id, "warehouse_id": warehouse_id, "qty": qty, "route_id": route_id,
         "reason": reason},
    )


def transfer_stock(
    store: EventStore,
    sku: str,
    qty: int,
    from_wh: str,
    to_wh: str,
    route_id: str,
    reason: str = "",
) -> dict:
    return store.append(
        TRANSFER_EVENT,
        {"sku": sku, "qty": qty, "from_wh": from_wh, "to_wh": to_wh,
         "route_id": route_id, "reason": reason},
    )


def reset_world() -> None:
    from simworld.events import reset_clock

    reset_clock()
    store = EventStore()
    store.clear()
    ensure_seeded(store)