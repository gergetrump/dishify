"""SQLAlchemy engine + session factory.

`DATABASE_URL` controls the backend:
	* unset / empty -> ``sqlite:///./dishify.db`` (file in repo root)
	* ``postgresql+psycopg://user:pass@host:5432/dbname`` for Postgres

SQLite is the default so the project works without Docker. The schema uses
generic ``JSON`` columns that map cleanly to both backends.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# Repo root: backend/app/db/base.py -> parents[3] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_database_url() -> str:
	url = os.getenv("DATABASE_URL", "").strip()
	if url:
		return url
	# Default to a SQLite file at the repo root so the path is stable regardless
	# of where the process happens to be launched from (uvicorn from backend/,
	# scripts from repo root, tests from anywhere).
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
	"""Create tables. Idempotent. Used by the loader script and tests."""

	from . import models  # noqa: F401  -- ensure models are imported for metadata

	Base.metadata.create_all(bind=engine)
