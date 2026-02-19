from asyncio import AbstractEventLoop
from pathlib import Path
from typing import Set

from pydantic import BaseModel

class Config(BaseModel):
    base: Path = Path(__file__).resolve().parents[3]
    media: Path = base / "media"
    log_file: Path = media / "mobile_app.log"
    data_base_path: Path = media / "data_base.sqlite3"

    global_event_loop: AbstractEventLoop

    dark_bg: Set = (0.15, 0.15, 0.15, 1)
    input_dg: Set = (0.25, 0.25, 0.25, 1)
    primary_btn: Set = (0.3, 0.6, 0.9, 1)
    secondary_btn: Set = (0.35, 0.35, 0.35, 1)
    text_color: Set = (1, 1, 1, 1)
    hint_color: Set = (0.7, 0.7, 0.7, 1)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def sqlite_url(self) -> str:
        """Возвращает полный URL для асинхронного подключения SQLAlchemy"""
        return f"sqlite+aiosqlite:///{self.data_base_path}"
