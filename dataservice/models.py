from __future__ import annotations
from typing import (
    Annotated,
    AsyncGenerator,
    Callable,
    Generator,
    Iterable,
    Iterator,
    Literal,
    Optional,
    TypeVar,
    Union,
    TYPE_CHECKING,
    Any,
)

from bs4 import BeautifulSoup
from pydantic import (
    AfterValidator,
    BaseModel,
    HttpUrl,
    model_validator,
    model_serializer,
)

from dataservice.abclient import ABClient

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
StrOrDict = str | dict

RequestsIterable = (
    Iterable["Request"]
    | Generator["Request", None, None]
    | AsyncGenerator["Request", None]
)


class Request(BaseModel):
    """Request model."""

    class Config:
        arbitrary_types_allowed = True

    url: Annotated[HttpUrl, AfterValidator(str)]
    callback: CallbackType
    method: Literal["GET", "POST"] = "GET"
    content_type: Literal["text", "json"] = "text"
    headers: Optional[dict] = None
    params: Optional[dict] = None
    form_data: Optional[dict] = None
    json_data: Optional[dict] = None
    client: type(ABClient)

    @model_validator(mode="after")
    def validate(self):
        if self.method == "POST" and not self.form_data and not self.json_data:
            raise ValueError("POST requests require either form data or json data.")
        if self.method == "GET" and (self.form_data or self.json_data):
            raise ValueError("GET requests cannot have form data or json data.")
        return self

    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        model = {}
        for key in self.model_fields.keys():
            val = getattr(self, key)
            if key in ("callback", "client"):
                val = id(val)
            model[key] = val
        return model


class Response(BaseModel):
    """Response model."""

    class Config:
        arbitrary_types_allowed = True

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
