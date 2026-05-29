"""Database engine factory for finances SQLite storage."""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from finances.models import metadata

_engine: Engine | None = None


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised; call init_engine() first")
    return _engine


def init_engine(db_path: str | Path = "finances.db") -> Engine:
    global _engine
    _engine = create_engine(f"sqlite:///{db_path}", future=True)
    return _engine


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)
