"""Logging module."""

from logging.config import dictConfig
from typing import Literal

from pydantic import BaseModel, Field

HandlerType = Literal["stdout", "file"]
LoggingLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class HandlerDict(BaseModel):
    class_: str = Field(alias="class", default="logging.StreamHandler")
    stream: str = "ext://sys.stdout"
    formatter: str = "simple"


class LoggerDict(BaseModel):
    handlers: list[HandlerType] = ["stdout"]
    level: LoggingLevel = "DEBUG"
    propagate: bool = False


class LoggingConfigDict(BaseModel):
    version: int = 1
    disable_existing_loggers: bool = False
    filters: dict[str, dict] = {}
    formatters: dict[str, dict] = {
        "simple": {"format": "%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s"},
    }
    handlers: dict[str, HandlerDict] = {"stdout": HandlerDict()}
    loggers: dict[str, LoggerDict] = {"dataservice": LoggerDict()}


def setup_logging(logger_name: str | None = None):
    """Setup logging configuration.

    :param logger_name: The logger name.
    """
    loggers = {"dataservice": LoggerDict()}
    if logger_name is not None:
        loggers.update({logger_name: LoggerDict()})

    dict_config = LoggingConfigDict(loggers=loggers).model_dump(by_alias=True)
    dictConfig(dict_config)
