import asyncio

from src.service.models.conf_model import Config

_config: Config = None
_event_loop = None

def init_conf():
    global _config

    _config = Config()


def set_config(conf: Config):
    global _config
    _config = conf


def get_config():
    global _config

    if _config is None:
        raise RuntimeError("Config не заполнен")

    return _config


def init_event_loop():
    global _event_loop
    _event_loop = asyncio.new_event_loop()
    return _event_loop

def get_event_loop():
    global _event_loop
    if _event_loop is None:
        raise RuntimeError("Event loop not initialized")
    return _event_loop