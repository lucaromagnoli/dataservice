import inspect
import typing
from typing import Callable, Iterator, TypeVar, Union, Literal
from bs4 import BeautifulSoup

from pydantic import BaseModel, AnyUrl, validator

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
ResponseData = str | dict


class Request(BaseModel):
    url: AnyUrl
    callback: CallbackType
    method: Literal["GET", "POST"] = "GET"
    content_type: Literal["text", "data"] = "text"

class Response(BaseModel):
    request: Request
    data: ResponseData
    soup: BeautifulSoup
