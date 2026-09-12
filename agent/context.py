"""Runtime context shared by all graph nodes.

Kept as a small mutable singleton so the same graph definition works against
SQLite (local dev), Postgres (docker), and in tests without threading state
through every node signature.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from config import CANDIDATE_CAP, VERIFY_MAX_ATTEMPTS
from simworld.events import EventStore
from simworld import world


@dataclass
class LLMClient:
    """Optional LLM for the decision-justification step.

    Any failure or slow response falls back to the deterministic "cheapest
    ranked candidate" path so a live demo never stalls on an API call.
    """
    enabled: bool = True
    provider: str = "off"
    model: str = "deterministic-fallback"
    responses: list = field(default_factory=list)

    def decide(self, prompt: dict[str, Any], default: str) -> dict[str, Any]:
        from agent.llm import llm_decide
        return llm_decide(self, prompt, default)


@dataclass
class AgentContext:
    store: EventStore = field(default_factory=EventStore)
    llm: LLMClient = field(default_factory=LLMClient)
    max_verify_attempts: int = VERIFY_MAX_ATTEMPTS
    candidate_cap: int = CANDIDATE_CAP
    _candidate_objs: dict = field(default_factory=dict)

    def snapshot(self, day: int | None = None) -> dict:
        return world.get_state(self.store, day)


ctx: AgentContext = AgentContext()