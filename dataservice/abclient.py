from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from logging import getLogger, LoggerAdapter, Filter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataservice import Request, Response

class ClassNameAdapter(LoggerAdapter):
    def process(self, msg, kwargs):
        return f'[{self.extra["class_name"]}] {msg}', kwargs

class ABClient(ABC):
    """Abstract base class for clients."""

    def __init__(self):
        self._logger = None
    @property
    def logger(self):
        if self._logger is None:
            self._logger = getLogger(__name__.split('.')[0])
            self._logger = ClassNameAdapter(self._logger, {"class_name": self.get_name()})
        return self._logger


    def get_name(self):
        return self.__class__.__name__

    @abstractmethod
    async def make_request(self, request: Request) -> Response:
        raise NotImplementedError
