"""SQLAlchemy engine + session factory."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    return f"sqlite:///{REPO_ROOT / 'dishify.db'}"


DATABASE_URL = _resolve_database_url()

_engine_kwargs: dict = {"future": True, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine: Engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_all() -> None:
    """Create tables. Idempotent."""

    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
