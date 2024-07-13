from typing import Callable, Iterator, Literal, TypeVar, Union, Optional

from bs4 import BeautifulSoup
from pydantic import AnyUrl, ConfigDict
from pydantic.dataclasses import dataclass


DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
StrOrDict = str | dict


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Request:
    """Request model."""

    url: AnyUrl
    callback: CallbackType
    method: Literal["GET", "POST"] = "GET"
    headers: Optional[dict] = None
    params: Optional[dict] = None
    data: Optional[dict] = None
    json: Optional[dict] = None
    content_type: Literal["text", "json"] = "text"
    client: Optional[str] = None


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Response:
    """Response model."""

    request: Request
    data: StrOrDict
    __soup: BeautifulSoup | None = None

    def __get_soup(self):
        if isinstance(self.data, dict):
            raise Warning("Cannot create BeautifulSoup from dict.")
        return BeautifulSoup(self.data, "html5lib")

    @property
    def soup(self) -> BeautifulSoup:
        if self.__soup is None:
            self.__soup = self.__get_soup()
        return self.__soup

