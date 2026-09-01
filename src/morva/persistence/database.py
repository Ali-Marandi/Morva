from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("MORVA_DATABASE_URL", "sqlite:///./morva.db")
ENVIRONMENT = os.getenv("MORVA_ENV", "development").lower()
if ENVIRONMENT in {"production", "prod"} and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite is forbidden in production; configure PostgreSQL")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from morva.persistence.models import Base

    Base.metadata.create_all(bind=engine)
