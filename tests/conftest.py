"""Pytest fixtures: isolated SQLite store + pinned simulated clock."""
from __future__ import annotations

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/simworld_test.db"
os.environ["SIM_DAY_SECONDS"] = "60"

from simworld.events import EventStore, init_db, set_sim_day
from simworld import world
from simworld.seed import seed_payload

import pytest


@pytest.fixture(autouse=True)
def fresh_world(monkeypatch):
    init_db()
    world.reset_world()
    set_sim_day(0)
    yield world
    # leave the world in a clean state for the next test
    world.reset_world()
    set_sim_day(0)