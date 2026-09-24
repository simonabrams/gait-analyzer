"""
SQLAlchemy engine and session for sync use (API and Celery worker).
"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models import Base

_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/gait_analyzer",
)
# Explicit +psycopg2 driver, not just "postgresql://": SQLAlchemy 2.1 changed
# the DBAPI it picks for a bare postgresql:// URL from psycopg2 to psycopg
# (v3) — which isn't installed here (only psycopg2-binary is, see
# requirements.txt), so create_engine() below raised ModuleNotFoundError the
# moment a fresh `pip install` picked up 2.1 (reproduced locally; broke CI's
# always-fresh install first — see the fresh-install/no-ceiling-pin failure
# mode ruff's own pin comment already describes). Being explicit here makes
# this immune to whatever SQLAlchemy's default becomes next, instead of
# re-pinning a version ceiling that just delays the same problem.
DATABASE_URL = _raw_url.replace("postgres://", "postgresql+psycopg2://", 1) if _raw_url.startswith("postgres://") \
    else _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1) if _raw_url.startswith("postgresql://") \
    else _raw_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    return SessionLocal()
