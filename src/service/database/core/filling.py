import logging

from sqlalchemy import create_engine

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
    engine = create_engine(conf.sqlite_url, echo=True)

    try:
        logging.info(f"Creating database tables at {conf.data_base_path}...")
        Base.metadata.create_all(engine)
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise
    finally:
        engine.dispose()


async def _create_table():
    """создает таблицы в целевой базе данных"""
    engine = create_engine(get_config().sqlite_url)
    try:
        logging.info("Creating core tables...")
        Base.metadata.create_all(engine)
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise
    finally:
        engine.dispose()


async def _filling_only_one_admin():
    async with get_db() as session_db:
        admins = session_db.query(User).filter(User.role == StorageStatus.ADMIN).all()

        if not admins:
            new_admin = User(
                login="admin",
                password=hash_password("admin"),
                role=StorageStatus.ADMIN
            )
            session_db.add(new_admin)

            session_db.commit()
