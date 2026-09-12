"""SimWorld + Agent — FastAPI endpoints (read-side, commands, disruption injector)."""
from __future__ import annotations

from typing import Any, Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import FRONTEND_ORIGIN
from agent.graph import run_agent, get_thread_state
from agent import tools
from simworld import world, disruptions
from simworld.disruptions import DISRUPTION_TYPES
from simworld.events import EventStore, init_db


@asynccontextmanager
async def lifespan(_app):
    init_db()
    world.ensure_seeded()
    yield


app = FastAPI(title="Agentic Supply Chain Recovery", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Read side (projections)
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "simworld + agent"}


@app.get("/state")
def state() -> dict:
    return world.get_state()


@app.get("/kpis")
def kpis() -> dict:
    return world.get_state()["kpis"]


@app.get("/inventory")
def inventory() -> dict:
    return world.get_state()["inventory"]


@app.get("/shipments")
def shipments() -> dict:
    return world.get_state()["shipments"]


@app.get("/orders")
def orders() -> dict:
    return world.get_state()["orders"]


@app.get("/vendors")
def vendors() -> dict:
    return world.get_state()["vendors"]


@app.get("/routes")
def routes() -> dict:
    return world.get_state()["routes"]


@app.get("/events")
def events(after: int = 0) -> list[dict]:
    store = EventStore()
    return store.events_since(after)


@app.get("/candidates")
def candidates(order_id: Optional[str] = None) -> dict:
    """Current alternative plan set for at-risk order(s), ranked by score."""
    st = world.get_state()
    risk = st["risk_orders"]
    if order_id:
        risk = [r for r in risk if r["order_id"] == order_id]
    c = __import__("optimizer.candidates", fromlist=["build_candidates"]).build_candidates(
        risk, st, st["sim_day"])
    return {"risk_orders": risk, "candidates": [p.asdict() for p in sorted(c, key=lambda p: p.score)]}


# ---------------------------------------------------------------------------
# Write side (commands → events)
# ---------------------------------------------------------------------------

class RerouteIn(BaseModel):
    shipment_id: str
    route_id: str


class OrderIn(BaseModel):
    order_id: str
    qty: int = Field(gt=0)
    route_id: str
    vendor_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    reason: str = ""


class TransferIn(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    from_wh: str
    to_wh: str
    route_id: str


class CancelIn(BaseModel):
    shipment_id: str


@app.post("/commands/reroute")
def cmd_reroute(body: RerouteIn) -> dict:
    return world.reroute_shipment(EventStore(), body.shipment_id, body.route_id)


@app.post("/commands/cancel")
def cmd_cancel(body: CancelIn) -> dict:
    return world.cancel_shipment(EventStore(), body.shipment_id)


@app.post("/commands/place_order")
def cmd_place_order(body: OrderIn) -> dict:
    if not body.vendor_id:
        raise HTTPException(400, "vendor_id required")
    return world.place_order(EventStore(), body.order_id, body.vendor_id, body.qty,
                             body.route_id, reason=body.reason)


@app.post("/commands/allocate")
def cmd_allocate(body: OrderIn) -> dict:
    if not body.warehouse_id:
        raise HTTPException(400, "warehouse_id required")
    return world.allocate_inventory(EventStore(), body.order_id, body.warehouse_id,
                                    body.qty, body.route_id, reason=body.reason)


@app.post("/commands/transfer")
def cmd_transfer(body: TransferIn) -> dict:
    return world.transfer_stock(EventStore(), body.sku, body.qty, body.from_wh,
                                body.to_wh, body.route_id)


# ---------------------------------------------------------------------------
# Disruption injector (manual chaos trigger — mandatory for the live demo)
# ---------------------------------------------------------------------------

class DisruptionIn(BaseModel):
    type: str
    params: dict[str, Any] = {}


@app.post("/disruptions/trigger")
def trigger_disruption(body: DisruptionIn) -> dict:
    if body.type not in DISRUPTION_TYPES:
        raise HTTPException(400, f"unknown disruption type. choose from {DISRUPTION_TYPES}")
    d = disruptions.build_disruption(body.type, body.params or None)
    events = d.apply()
    return {"disruption": body.type, "label": d.label, "params": d.params, "events": events}


@app.get("/disruptions/types")
def disruption_types() -> dict:
    return {"types": list(DISRUPTION_TYPES)}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@app.post("/agent/run")
def agent_run(thread_id: Optional[str] = None) -> dict:
    result = run_agent(thread_id)
    return result


@app.get("/agent/trace/{thread_id}")
def agent_trace(thread_id: str) -> dict:
    st = get_thread_state(thread_id)
    if not st:
        raise HTTPException(404, f"no run found for {thread_id}")
    return {
        "run_id": thread_id,
        "trace": st["trace"] if "trace" in st else [],
        "status": st.get("status"),
        "decision": st.get("decision"),
        "verification": st.get("verification"),
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

@app.post("/reset")
def reset() -> dict:
    world.reset_world()
    return {"status": "reset", "state": world.get_state()}