"""LangGraph state machine — the agent's workflow.

    monitor → detect ──no violations──▶ END
                  │
                  └─violations──▶ retrieve → optimize → decide → execute → verify
                                                                      │ pass → END
                                                                      │ fail & attempts left → retrieve (replan, failed candidate excluded)
                                                                      └ fail twice → escalate → END
"""
from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agent.context import ctx
from agent.nodes import (
    decide,
    detect,
    escalate,
    execute,
    monitor,
    optimize,
    retrieve,
    verify,
)
from agent.state import AgentState, new_state


def route_after_detect(state: AgentState) -> str:
    return "end" if not state.get("issues") else "retrieve"


def route_after_verify(state: AgentState) -> str:
    passed = state.get("verification", {}).get("passed", False)
    if passed:
        return "satisfied"
    if state.get("replan_count", 0) >= ctx.max_verify_attempts:
        return "escalate"
    return "retrieve"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("monitor", monitor.monitor)
    g.add_node("detect", detect.detect)
    g.add_node("retrieve", retrieve.retrieve)
    g.add_node("optimize", optimize.optimize)
    g.add_node("decide", decide.decide)
    g.add_node("execute", execute.execute)
    g.add_node("verify", verify.verify)
    g.add_node("escalate", escalate.escalate)

    g.add_edge(START, "monitor")
    g.add_edge("monitor", "detect")
    g.add_conditional_edges(
        "detect",
        route_after_detect,
        {"retrieve": "retrieve", "end": END},
    )
    g.add_edge("retrieve", "optimize")
    g.add_edge("optimize", "decide")
    g.add_edge("decide", "execute")
    g.add_edge("execute", "verify")
    g.add_conditional_edges(
        "verify",
        route_after_verify,
        {"satisfied": END, "retrieve": "retrieve", "escalate": "escalate"},
    )
    g.add_edge("escalate", END)

    return g.compile(checkpointer=InMemorySaver())


graph = build_graph()


def run_agent(thread_id: str | None = None) -> AgentState:
    """Run the agent to convergence and return the final, checkpointed state."""
    run_id = thread_id or f"run-{uuid.uuid4().hex[:10]}"
    state = new_state()
    state["run_id"] = run_id
    config = {"configurable": {"thread_id": run_id}}
    result = graph.invoke(state, config=config)
    result["run_id"] = run_id
    return result


def get_thread_state(thread_id: str) -> AgentState | None:
    """Read a previous run's persistent task state from the checkpointer."""
    config = {"configurable": {"thread_id": thread_id}}
    snap = graph.get_state(config)
    if snap is None or snap.values is None:
        return None
    return snap.values