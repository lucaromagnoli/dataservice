"""Logging module."""

import logging
from typing import Literal

from pydantic import BaseModel, Field

HandlerType = Literal["stdout", "file"]
LoggingLevel = Literal["INFO", "DEBUG", "WARNING", "ERROR"]


class Handler(BaseModel):
    class_: str = Field(alias="class", default="logging.StreamHandler")
    stream: str = "ext://sys.stdout"
    formatter: str = "simple"


class Handlers(BaseModel):
    stdout: Handler = Handler()


class LoggerDict(BaseModel):
    handlers: list[HandlerType] = ["stdout"]
    level: LoggingLevel = "DEBUG"
    propagate: bool = False


class LoggingConfigDict(BaseModel):
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict[str, dict] = {
        "simple": {"format": "%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s"},
    }
    handlers: Handlers = Handlers()
    loggers: dict[str, LoggerDict] = {"dataservice": LoggerDict()}


def setup_logging(config_dict: LoggingConfigDict | None = None):
    if config_dict is None:
        config_dict = LoggingConfigDict().model_dump(by_alias=True)
    logging.config.dictConfig(config_dict)
