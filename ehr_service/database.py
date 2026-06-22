from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ehr_service.models import Base

DEFAULT_DATABASE_URL = "sqlite:///./ehr.db"
SessionFactory = sessionmaker[Session]


def database_url() -> str:
    return os.environ.get("EHR_DATABASE_URL", DEFAULT_DATABASE_URL)


def engine_args(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def make_session_factory(url: str) -> SessionFactory:
    engine = create_engine(url, future=True, **engine_args(url))
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(session_factory: SessionFactory) -> None:
    Base.metadata.create_all(session_factory.kw["bind"])
