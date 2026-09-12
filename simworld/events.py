"""Append-only event store + simulated clock.

The event log is the single source of truth. Nothing ever mutates state
directly: agent actions and disruption injections append events, and the
projection layer replays them.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import Column, JSON, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL, SIM_DAY_SECONDS, SIM_START

Base = declarative_base()


class EventRow(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seq = Column(Integer, nullable=False, unique=True)
    day = Column(Integer, nullable=False)
    type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(String(32), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "seq": self.seq,
            "day": self.day,
            "type": self.type,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }


def make_engine(url: str = DATABASE_URL):
    if url.startswith("sqlite"):
        db_path = url.split("///", 1)[-1]
        if db_path and not db_path.startswith(":"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def init_db(url: Optional[str] = None) -> None:
    """Create tables. Use the same session as the rest of the process."""
    global engine, SessionLocal
    if url is not None:
        engine = make_engine(url)
        SessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Simulated clock (1 real minute = 1 simulated day by default)
# ---------------------------------------------------------------------------

_SIM_START_TS: Optional[datetime] = None


def _start_ts() -> datetime:
    global _SIM_START_TS
    if _SIM_START_TS is None:
        if SIM_START:
            _SIM_START_TS = datetime.fromisoformat(SIM_START)
        else:
            _SIM_START_TS = datetime.now(timezone.utc)
    return _SIM_START_TS


def reset_clock() -> None:
    global _SIM_START_TS
    _SIM_START_TS = None


def sim_day() -> int:
    """Current simulated day number, derived from elapsed wall-clock time."""
    return int((datetime.now(timezone.utc) - _start_ts()).total_seconds() / SIM_DAY_SECONDS)


def set_sim_day(day: int) -> None:
    """Pin the clock to a fixed simulated day (used by scenario tests)."""
    global _SIM_START_TS
    _SIM_START_TS = datetime.now(timezone.utc) - timedelta(seconds=day * SIM_DAY_SECONDS)


class EventStore:
    """Append-only store over SQLAlchemy sessions. All writes go through here."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def append(self, type: str, payload: dict[str, Any], day: Optional[int] = None) -> dict:
        """Append one event; returns the persisted row as dict."""
        with self._session_factory() as session:
            nxt = self._next_seq(session)
            row = EventRow(
                seq=nxt,
                day=sim_day() if day is None else day,
                type=type,
                payload=json.loads(json.dumps(payload)),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            session.add(row)
            session.commit()
            return row.to_dict()

    def append_many(self, events: list[tuple[str, dict, Optional[int]]]) -> list[dict]:
        with self._session_factory() as session:
            rows = []
            nxt = self._next_seq(session)
            for type, payload, day in events:
                row = EventRow(
                    seq=nxt,
                    day=sim_day() if day is None else day,
                    type=type,
                    payload=json.loads(json.dumps(payload)),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                session.add(row)
                rows.append(row)
                nxt += 1
            session.commit()
            return [r.to_dict() for r in rows]

    def _next_seq(self, session) -> int:
        existing = session.scalar(select(EventRow.seq).order_by(EventRow.seq.desc()).limit(1))
        return 0 if existing is None else existing + 1

    def events(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(EventRow).order_by(EventRow.seq.asc())
            ).all()
            return [r.to_dict() for r in rows]

    def events_since(self, seq: int) -> list[dict]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(EventRow).where(EventRow.seq >= seq).order_by(EventRow.seq.asc())
            ).all()
            return [r.to_dict() for r in rows]

    def last_seq(self) -> int:
        with self._session_factory() as session:
            existing = session.scalar(select(EventRow.seq).order_by(EventRow.seq.desc()).limit(1))
            return -1 if existing is None else existing

    def store_empty(self) -> bool:
        with self._session_factory() as session:
            return session.scalar(select(EventRow.id).limit(1)) is None

    def clear(self) -> None:
        with self._session_factory() as session:
            session.query(EventRow).delete()
            session.commit()