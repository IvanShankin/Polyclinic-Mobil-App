from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base_sqlalchemy = declarative_base()
_engine = None
_session_factory: Optional[sessionmaker] = None

class Base(Base_sqlalchemy):
    __abstract__ = True

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        from src.config import get_config

        conf = get_config()
        _engine = create_engine(conf.sqlite_url, echo=True)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)

    return _engine


def _get_session() -> Session:
    if _session_factory is None:
        _get_engine()
    return _session_factory()


@asynccontextmanager
async def get_db() -> Session:
    session = _get_session()
    try:
        yield session
    finally:
        session.close()
