from abc import ABC, abstractmethod
from logging import getLogger

from dataservice.models import Request, Response


class Client(ABC):
    """Abstract base class for clients."""
    def __init__(self):
        self.logger = getLogger(__name__)

    def get_name(self):
        return self.__class__.__name__

    @abstractmethod
    async def make_request(self, request: Request) -> Response:
        raise NotImplementedError


