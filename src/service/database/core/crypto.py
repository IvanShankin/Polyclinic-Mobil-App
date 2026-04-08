import base64
import hashlib
from typing import Optional

from src.config import get_config


_KEY: Optional[bytes] = None


def _get_key() -> bytes:
    global _KEY
    if _KEY is None:
        conf = get_config()
        seed = f"{conf.base}:{conf.data_base_path}".encode("utf-8")
        _KEY = hashlib.sha256(seed).digest()
    return _KEY


def encrypt_text(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return "" if value == "" else None

    data = value.encode("utf-8")
    key = _get_key()
    transformed = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(transformed).decode("ascii")


def decrypt_text(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return "" if value == "" else None

    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, TypeError):
        return value

    key = _get_key()
    original = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return original.decode("utf-8", errors="ignore")
