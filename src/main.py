import asyncio

from src.config import get_config, init_conf
from src.service.utils.core_logger import setup_logging


async def main():
    async_loop = asyncio.new_event_loop()
    init_conf()
    setup_logging(get_config().log_file)
    AuthApp().run()


if __name__ == "__main__":
    asyncio.run(main())