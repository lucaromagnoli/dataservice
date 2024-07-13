from typing import Callable, Iterator, Literal, TypeVar, Union, Optional

from bs4 import BeautifulSoup
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
StrOrDict = str | dict


@dataclass
class Request:
    url: AnyUrl
    callback: CallbackType
    method: Literal["GET", "POST"] = "GET"
    content_type: Literal["text", "json"] = "text"
    client: Optional[str] = None


class Response:
    def __init__(self, request: Request, data: StrOrDict):
        self.request = request
        self.data = data
        self.__soup = None

    def __get_soup(self):
        if isinstance(self.data, dict):
            raise Warning("Cannot create BeautifulSoup from dict.")
        return BeautifulSoup(self.data, "html5lib")

    @property
    def soup(self) -> BeautifulSoup:
        if self.__soup is None:
            self.__soup = self.__get_soup()
        return self.__soup
