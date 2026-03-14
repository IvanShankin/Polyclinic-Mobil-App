import os
import sys
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import Set

from pydantic import BaseModel


def get_base_dir() -> Path:
    """
    Возвращает правильную базовую директорию:
    - dev режим → root_dir
    - exe режим → папка где лежит exe
    """
    if getattr(sys, "frozen", False):
        # exe режим
        return Path(sys.executable).parent
    else:
        # dev режим
        return Path(__file__).resolve().parents[3]


class Config(BaseModel):
    base: Path = get_base_dir()

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
        return f"sqlite+aiosqlite:///{self.data_base_path}"


# создаём папку media гарантированно
os.makedirs(get_base_dir() / "media", exist_ok=True)