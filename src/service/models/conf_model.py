from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    base: Path = Path(__file__).resolve().parents[3]
    media: Path = base / Path("media")
    log_file: Path = media / Path("mobile_app.log")
    data_base_path: Path = media / Path("data_base.sqlite3")

    model_config = {
        "arbitrary_types_allowed": True,
    }