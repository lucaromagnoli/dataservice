import pytest

from dataservice.logs import LoggerDict, LoggingConfigDict, setup_logging


@pytest.fixture
def init_config_dict():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s",
            }
        },
        "filters": {},
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
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }


def test_init_config_dict(init_config_dict):
    config_dict = LoggingConfigDict().model_dump(by_alias=True)
    assert config_dict == init_config_dict


def test_setup_logging_default(mocker):
    mocked_dict_config = mocker.patch("dataservice.logs.dictConfig")
    setup_logging()
    mocked_dict_config.assert_called_once_with(
        LoggingConfigDict().model_dump(by_alias=True)
    )


def test_logging_config_custom(init_config_dict):
    assert (
        LoggingConfigDict(loggers={"dataservice": LoggerDict()}).model_dump(
            by_alias=True
        )
        == init_config_dict
    )


def test_setup_logging_custom(mocker):
    mocked_dict_config = mocker.patch("dataservice.logs.dictConfig")
    setup_logging("custom_logger")
    mocked_dict_config.assert_called_once_with(
        LoggingConfigDict(
            loggers={"dataservice": LoggerDict(), "custom_logger": LoggerDict()}
        ).model_dump(by_alias=True)
    )
