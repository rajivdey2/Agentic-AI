"""AgentState schema (shared by all nodes + the checkpointed run)."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # run identity
    run_id: str
    day: int
    status: str            # monitor | detect | retrieve | optimize | decide | execute | verify | escalated | satisfied
    message: str

    # read-side (projection)
    projection: dict[str, Any]
    issues: list[dict[str, Any]]
    risk_orders: list[dict[str, Any]]

    # planning
    candidates: list[dict[str, Any]]
    solver: dict[str, Any]
    decision: dict[str, Any]
    actions: list[dict[str, Any]]

    # execution
    executed: list[dict[str, Any]]

    # verification / adaptation
    verification: dict[str, Any]
    replan_count: int
    excluded: list[str]

    # audit
    trace: list[dict[str, Any]]


def new_state() -> AgentState:
    return {
        "run_id": "run-0",
        "day": 0,
        "status": "monitor",
        "message": "",
        "issues": [],
        "risk_orders": [],
        "candidates": [],
        "solver": {},
        "decision": {},
        "actions": [],
        "executed": [],
        "verification": {},
        "replan_count": 0,
        "excluded": [],
        "trace": [],
    }