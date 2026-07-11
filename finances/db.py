"""Database engine factory for finances SQLite storage."""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from finances.models import metadata


def get_engine(db_path: str | Path = "finances.db") -> Engine:
    return create_engine(f"sqlite:///{db_path}", future=True)


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)
