import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import get_config
from src.service.database.actions.actions import hash_password
from src.service.database.core.database import Base, get_db
from src.service.database.models import User, StorageStatus



async def filling_db():
    await _create_database()
    await _create_table()

    await _filling_only_one_admin()


async def _create_database():
    """
    Создаёт файл SQLite базы данных и все таблицы.
    Если файл существует — ничего не ломает.
    """
    conf = get_config()
    engine = create_async_engine(conf.sqlite_url, echo=True)

    try:
        async with engine.begin() as conn:
            logging.info(f"Creating database tables at {conf.data_base_path}...")
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()


async def _create_table():
    """создает таблицы в целевой базе данных"""
    engine = create_async_engine(get_config().sqlite_url)
    try:
        async with engine.begin() as conn:
            logging.info("Creating core tables...")
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()


async def _filling_only_one_admin():
    async with get_db() as session_db:
        result_db = await session_db.execute(select(User).where(User.role == StorageStatus.ADMIN))
        admins = result_db.scalars().all()

        if not admins:
            new_admin = User(
                login="admin",
                password=hash_password("admin"),
                role=StorageStatus.ADMIN
            )
            session_db.add(new_admin)

            await session_db.commit()
