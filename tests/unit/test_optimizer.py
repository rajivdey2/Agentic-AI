"""Optimizer unit checks: ranking, capacity & stock constraints, exclusion."""
from __future__ import annotations

import pytest

from simworld import world, disruptions
from simworld.events import EventStore, set_sim_day
from optimizer.candidates import build_candidates
from optimizer.solvers import solve


@pytest.fixture
def delayed():
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("shipment_delay", {"shipment_id": "S-3", "delay_days": 7}).apply(store)
    return store


def test_candidates_ranked_by_score(delayed):
    st = world.get_state(delayed)
    cands = build_candidates(st["risk_orders"], st, st["sim_day"])
    assert cands
    scores = [c.score for c in cands]
    assert scores == sorted(scores)
    # local same-city vendor should out-rank long air freight
    assert cands[0].source_kind == "allocate" or cands[0].source_location == "MUM"


def test_solver_returns_optimal_without_overrun(delayed):
    st = world.get_state(delayed)
    res = solve(build_candidates(st["risk_orders"], st, st["sim_day"]), st, st["sim_day"])
    assert res["status"] == "optimal"
    assert res["selected"]
    assert res["unfulfilled_orders"] == []
    assert res["delta_cost"] <= st["kpis"]["remaining_budget"]

    chosen = res["selected"][0]
    assert chosen["order_id"] == "O-3"
    assert chosen["cancel_shipment_ids"] == ["S-3"]
    assert chosen["eta"] <= chosen["deadline"]


def test_solver_respects_excluded_candidates(delayed):
    """A candidate verification already rejected must never be offered again."""
    st = world.get_state(delayed)
    cands = build_candidates(st["risk_orders"], st, st["sim_day"])
    rejected = {"PLAN-O-3-purchase-V-MUM-R_MUM_MUM"}
    cands2 = build_candidates(st["risk_orders"], st, st["sim_day"],
                              excluded_candidates=rejected)
    assert all(c.id not in rejected for c in cands2)
    res = solve(cands2, st, st["sim_day"])
    assert all(p["id"] not in rejected for p in res["selected"])


def test_solver_respects_vendor_capacity():
    store = EventStore()
    set_sim_day(0)
    disruptions.build_disruption("shipment_delay", {"shipment_id": "S-3", "delay_days": 7}).apply(store)
    disruptions.build_disruption("vendor_capacity_drop", {"vendor_id": "V-MUM", "new_capacity": 0}).apply(store)
    st = world.get_state(store)
    res = solve(build_candidates(st["risk_orders"], st, st["sim_day"]), st, st["sim_day"])
    for p in res["selected"]:
        if p["source_kind"] == "purchase":
            assert p["source_id"] != "V-MUM"


def test_solver_infeasible_when_no_candidates():
    store = EventStore()
    set_sim_day(0)
    # absurd demand spike: no vendor/warehouse can cover 100k units
    disruptions.build_disruption("demand_spike", {"order_id": "O-3", "new_qty": 100_000}).apply(store)
    st = world.get_state(store)
    cands = build_candidates(st["risk_orders"], st, st["sim_day"])
    res = solve(cands, st, st["sim_day"])
    assert res["status"] == "infeasible" or not res["selected"] or bool(res["unfulfilled_orders"])