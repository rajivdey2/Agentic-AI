"""Optional LLM reasoning step for `decide_action`.

The optimizer produces a provably-ranked candidate set; the LLM's job is to
explain which plan was chosen and justify the trade-off. Calling the API is
best-effort: on any failure, timeout, or missing key we fall back to the
already-computed cheapest ranked candidate, so a slow API can never stall the
live demo.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from config import (
    LLM_TIMEOUT_SECONDS,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_BASE_URL,
)

# Model ids are tried in order; account/plans differ on availability and
# Anthropic occasionally retires aliases (which shows up as a 404).
_ANTHROPIC_MODELS = [
    "claude-3-5-haiku-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-7-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-sonnet-4-20250514",
]
_OPENAI_MODELS = ["gpt-4o-mini", "gpt-4o"]


def _pick_default(prompt: dict[str, Any]) -> dict[str, Any]:
    ranked = prompt.get("ranked_candidates", [])
    chosen = ranked[0] if ranked else None
    base = {
        "choice": (chosen or {}).get("id"),
        "justification": "Deterministic fallback: lowest weighted score "
                         "(cost/time/carbon) among ranked candidates.",
        "provider": "deterministic-fallback",
        "model": "none",
        "latency_ms": 0,
    }
    if chosen:
        base["summary"] = (
            f"Plan {chosen['id']}: {chosen['qty']} units of {chosen['sku']} for "
            f"{chosen['order_id']} via {'vendor' if chosen['source_kind']=='purchase' else chosen['source_kind']} "
            f"{chosen['source_id']}, route {chosen['route_id']} (ETA day {chosen['eta']}, "
            f"cost {chosen['total_cost']}, carbon {chosen['total_carbon']})."
        )
    return base


def _anthropic_prompt(prompt: dict[str, Any]) -> str:
    selected = prompt.get("selected", [])
    ranked = prompt.get("ranked_candidates", [])
    sel_ids = ", ".join(c.get("id", "?") for c in selected) or "none"
    lines = [f"The optimizer has already chosen these plans (must match choice): {sel_ids}\n",
             "Ranked candidates (lower score = better trade-off):"]
    for c in ranked:
        lines.append(
            f"  [{c['id']}] {c['qty']} {c['sku']} for {c['order_id']} via "
            f"{c['source_kind']}/{c['source_id']}, route {c['route_id']} "
            f"(ETA day {c['eta']}, cost {c['total_cost']}, carbon {c['total_carbon']}, "
            f"score {c['score']:.2f})"
        )
    return "\n".join(lines)


def _call_provider(provider: str, prompt: dict[str, Any], api_key: str) -> dict[str, Any]:
    base = GROQ_BASE_URL if provider == "groq" else "https://api.openai.com/v1"
    models = GROQ_MODEL if provider == "groq" else _OPENAI_MODELS
    user_content = (
        "You are a supply chain recovery agent explaining your recovery "
        "decisions to a human operator. The optimizer already selected a set "
        "of recovery plans. Your job is ONLY to write a concise 2-3 sentence "
        "justification of the chosen trade-off (cost / delivery-time / carbon). "
        "Respond ONLY with JSON: {\"choice\": \"<chosen plan id from the selected "
        "list>\", \"justification\": \"<2-3 sentences>\"}.\n\n"
        + _anthropic_prompt(prompt)
    )
    if provider == "anthropic":
        req = {
            "max_tokens": 300,
            "messages": [{"role": "user", "content": user_content}],
        }
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            last_status = 0
            last_detail = ""
            for model in _ANTHROPIC_MODELS:
                req["model"] = model
                r = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                    json=req,
                )
                last_status = r.status_code
                if r.status_code == 200:
                    result = r.json()
                    result["_model"] = model
                    return result
                last_detail = r.json().get("error", {}).get("message", r.text[:200])
            raise httpx.HTTPStatusError(
                f"Anthropic: no model accepted (last status {last_status}): {last_detail}",
                request=None, response=None)
    else:  # openai-compatible (openai / groq)
        req = {
            "max_tokens": 300,
            "messages": [{"role": "user", "content": user_content}],
        }
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            last_status = 0
            last_detail = ""
            model = ""
            for model in ([models] if isinstance(models, str) else models):
                req["model"] = model
                r = client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=req,
                )
                last_status = r.status_code
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    parsed["_model"] = model
                    return parsed
                last_detail = r.json().get("error", {}).get("message", r.text[:200])
            raise httpx.HTTPStatusError(
                f"{provider}: no model accepted (last status {last_status}): {last_detail}",
                request=None, response=None)


def llm_decide(client: Any, prompt: dict[str, Any], default: dict[str, Any]) -> dict[str, Any]:
    """Best-effort LLM decision with a deterministic fallback. Never raises."""
    if not client.enabled:
        default["llm_error"] = "llm disabled"
        return default

    api_key = ANTHROPIC_API_KEY or GROQ_API_KEY or OPENAI_API_KEY
    if GROQ_API_KEY:
        provider, api_key = "groq", GROQ_API_KEY
    elif ANTHROPIC_API_KEY:
        provider, api_key = "anthropic", ANTHROPIC_API_KEY
    elif OPENAI_API_KEY:
        provider, api_key = "openai", OPENAI_API_KEY
    else:
        provider = ""
    if not api_key or provider not in ("anthropic", "openai", "groq"):
        default["llm_error"] = "no api key configured in the server process"
        return default

    t0 = time.time()
    try:
        result = _call_provider(provider, prompt, api_key)
        latency = int((time.time() - t0) * 1000)
        if provider == "anthropic":
            text = result["content"][0]["text"]
        else:
            text = json.dumps(result)
        parsed = json.loads(text)
        choice = str(parsed.get("choice", "")).strip()
        ranked = prompt.get("ranked_candidates", [])
        chosen = next((c for c in ranked if c["id"] == choice), None)
        if chosen is None:
            default["llm_error"] = f"{provider} returned an unknown choice"
            return default
        return {
            "choice": chosen["id"],
            "justification": str(parsed.get("justification", "")).strip(),
            "provider": provider,
            "model": result.get("_model", "unknown"),
            "latency_ms": latency,
            "summary": default.get("summary", ""),
        }
    except Exception as exc:  # noqa: BLE001
        default["llm_error"] = f"{type(exc).__name__}: {str(exc)[:220]}"
        return default