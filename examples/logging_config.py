import logging.config


def setup_logging():
    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
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
            "dataservice": {
                "handlers": ["stdout"],
                "level": "INFO",
                "propagate": False,
            },
            "dataservice": {
                "handlers": ["stdout"],
                "level": "INFO",
                "propagate": False,
            },
            "books_scraper": {
                "handlers": ["stdout"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(config_dict)
