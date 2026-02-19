from contextlib import asynccontextmanager
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base_sqlalchemy = declarative_base()

class Base(Base_sqlalchemy):
    __abstract__ = True

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

@asynccontextmanager
async def get_db() -> AsyncSession:
    from src.config import get_config

    conf = get_config()
    async_session_factory = sessionmaker(
        create_async_engine(conf.sqlite_url, echo=True),
        expire_on_commit=False,
        class_=AsyncSession
    )

    async with async_session_factory() as session:
        yield session
