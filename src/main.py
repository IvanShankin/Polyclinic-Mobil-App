import asyncio

from src.config import get_config, init_conf
from src.service.database.core.filling import filling_db
from src.service.utils.core_logger import setup_logging
from src.ui.main_ui import AuthApp


async def main():
    init_conf()
    setup_logging(get_config().log_file)

    await filling_db()

    AuthApp().run()


if __name__ == "__main__":
    asyncio.run(main())