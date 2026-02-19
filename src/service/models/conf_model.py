from asyncio import AbstractEventLoop
from pathlib import Path
from pydantic import BaseModel

class Config(BaseModel):
    base: Path = Path(__file__).resolve().parents[3]
    media: Path = base / "media"
    log_file: Path = media / "mobile_app.log"
    data_base_path: Path = media / "data_base.sqlite3"

    global_event_loop: AbstractEventLoop

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def sqlite_url(self) -> str:
        """Возвращает полный URL для асинхронного подключения SQLAlchemy"""
        return f"sqlite+aiosqlite:///{self.data_base_path}"
