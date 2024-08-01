import logging.config

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {
            "format": "%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "simple",
        }
    },
    "loggers": {
        "dataservice": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}


logging.config.dictConfig(LOGGING)
