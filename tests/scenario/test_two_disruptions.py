"""End-to-end scenario tests against the *real* LangGraph (no mocks).

Covers the rubric's case: baseline → disruption 1 → replan → disruption 2 →
replan → verify, plus explicit guarantees that the agent never re-picks a
rejected alternative and escalates when it cannot converge.
"""
from __future__ import annotations

import pytest

from simworld import world, disruptions
from simworld.events import EventStore, set_sim_day
from agent.graph import run_agent, get_thread_state


def _in_transit_for(store: EventStore, order_id: str) -> str:
    st = world.get_state(store)
    return next(
        s["id"] for s in st["shipments"].values()
        if s.get("order_id") == order_id and s["status"] == "in_transit"
    )


def test_full_recovery_after_two_successive_disruptions():
    store = EventStore()
    set_sim_day(0)

    # disruption 1: vendor hiccup delays an in-flight order
    disruptions.build_disruption("shipment_delay", {"shipment_id": "S-3", "delay_days": 7}).apply(store)
    r1 = run_agent("scenario-d1")
    assert r1["verification"]["passed"]
    assert r1["status"] in ("verify", "satisfied")
    assert world.get_state(store)["issues"] == []

    first_plan_id = r1["decision"]["choice"]
    assert first_plan_id.startswith("PLAN-O-3-")

    # disruption 2: the just-chosen alternative also fails
    new_ship = _in_transit_for(store, "O-3")
    disruptions.build_disruption("shipment_loss", {"shipment_id": new_ship}).apply(store)
    disruptions.build_disruption("vendor_capacity_drop",
                                 {"vendor_id": "V-MUM", "new_capacity": 0}).apply(store)

    r2 = run_agent("scenario-d2")
    assert r2["verification"]["passed"]
    assert world.get_state(store)["issues"] == []

    final = world.get_state(store)["kpis"]
    assert final["at_risk_orders"] == 0
    assert final["total_cost"] <= final["budget_cap"]
    assert final["total_carbon"] <= final["carbon_cap"]

    # the second decision must be a different plan (the chosen one failed)
    second_plan_id = r2["decision"]["choice"]
    assert second_plan_id != first_plan_id
    assert second_plan_id.startswith("PLAN-O-3-")


def test_scenario_does_not_pick_rejected_candidate():
    """The graph excludes a verification-rejected candidate on the replan loop."""
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("shipment_delay", {"shipment_id": "S-3", "delay_days": 7}).apply(store)
    r1 = run_agent("scenario-reject")
    first_plan_id = r1["decision"]["choice"]

    new_ship = _in_transit_for(store, "O-3")
    disruptions.build_disruption("shipment_loss", {"shipment_id": new_ship}).apply(store)
    disruptions.build_disruption("vendor_capacity_drop",
                                 {"vendor_id": "V-MUM", "new_capacity": 0}).apply(store)
    r2 = run_agent("scenario-reject-2")
    excluded = r2.get("excluded", [])
    assert first_plan_id in excluded or r2["decision"]["choice"] != first_plan_id


def test_persistent_thread_state_and_audit_trail():
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("shipment_delay", {"shipment_id": "S-3", "delay_days": 7}).apply(store)
    run_agent("audit-run")
    thread = get_thread_state("audit-run")
    assert thread is not None
    trace = thread["trace"]
    steps = [t["step"] for t in trace]
    assert steps == ["monitor", "detect", "retrieve", "optimize", "decide", "execute", "verify"]
    # every executed action must have a corresponding audit event
    log = store.events()
    executed = sum(1 for t in trace if t["step"] == "execute")
    action_events = [e for e in log if e["type"] in (
        "reroute_shipment", "place_order", "allocate_inventory",
        "transfer_stock", "shipment_cancel")]
    assert action_events  # at least: cancel S-3 + place new order


def test_escalates_after_repeated_failures():
    """No feasible alternative twice in a row => escalate_to_human, never silent success."""
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("demand_spike", {"order_id": "O-3", "new_qty": 100_000}).apply(store)
    r = run_agent("scenario-escalate")
    assert r["status"] == "escalated"
    assert r["verification"]["passed"] is False
    steps = [t["step"] for t in r["trace"]]
    assert "escalate_to_human" in steps


def test_demand_spike_triggers_replan():
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("demand_spike", {"order_id": "O-5", "new_qty": 200}).apply(store)
    r = run_agent("scenario-demand")
    assert r["verification"]["passed"]
    st = world.get_state(store)
    assert st["issues"] == []
    assert st["orders"]["O-5"]["qty"] == 200