from src.service.models.conf_model import Config

_config: Config = None


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