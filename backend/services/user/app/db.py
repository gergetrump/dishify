from __future__ import annotations

from pathlib import Path

from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def normalize_database_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def init_db() -> None:
    global _pool
    if _pool is not None:
        return

    conninfo = normalize_database_url(settings.database_url)
    _pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=5, open=True)
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with _pool.connection() as conn:
        conn.execute(schema_sql)
        conn.commit()


def close_db() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Database not initialized")
    return _pool
