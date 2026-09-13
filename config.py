"""Central configuration for the recovery agent.

Environment-overridable so the same code runs against SQLite locally and
PostgreSQL under docker-compose.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'data' / 'simworld.db').as_posix()}",
)

# Simulated clock: 1 real second = SIM_DAY_SECONDS simulated day (default 60s/day)
SIM_DAY_SECONDS = float(os.getenv("SIM_DAY_SECONDS", "60"))
SIM_START = os.getenv("SIM_START")  # ISO timestamp, optional fixed start

# Objective weights used by the optimizer
OBJ_WEIGHT_COST = float(os.getenv("OBJ_WEIGHT_COST", "1.0"))
OBJ_WEIGHT_TIME = float(os.getenv("OBJ_WEIGHT_TIME", "0.5"))
OBJ_WEIGHT_CARBON = float(os.getenv("OBJ_WEIGHT_CARBON", "0.3"))

# Agent runtime
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
VERIFY_MAX_ATTEMPTS = int(os.getenv("VERIFY_MAX_ATTEMPTS", "2"))
CANDIDATE_CAP = int(os.getenv("CANDIDATE_CAP", "15"))
SOLVER_TIME_LIMIT_SECONDS = float(os.getenv("SOLVER_TIME_LIMIT_SECONDS", "2.0"))

# API keys for the optional LLM justification step (deterministic fallback otherwise)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Groq (OpenAI-compatible) provider
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Gemini (OpenAI-compatible endpoint)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/v1",
)

# OpenRouter (OpenAI-compatible aggregator)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-vl:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")