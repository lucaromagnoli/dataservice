from __future__ import annotations

from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Iterable,
    Iterator,
    Literal,
    Optional,
    TypedDict,
    TypeVar,
    Union,
)

from bs4 import BeautifulSoup
from pydantic import (
    AfterValidator,
    BaseModel,
    HttpUrl,
    model_serializer,
    model_validator,
)

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
ClientCallable = Callable[["Request"], "Response"]
StrOrDict = str | dict


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
    client: ClientCallable

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
                val = type(val).__name__
            model[key] = val
        return model


class Response(BaseModel):
    """Response model."""

    class Config:
        arbitrary_types_allowed = True

    request: Request
    data: StrOrDict | None
    status_code: int = 200
    __soup: BeautifulSoup | None = None

    @property
    def soup(self) -> BeautifulSoup:
        if self.__soup is None:
            if isinstance(self.data, dict):
                raise ValueError("Cannot create BeautifulSoup from dict.")
            if self.data is not None:
                self.__soup = BeautifulSoup(self.data, "html5lib")
            else:
                self.__soup = BeautifulSoup("", "html5lib")
        return self.__soup


class FailedRequest(TypedDict):
    """Failed request model."""

    request: Request
    error: str


RequestsIterable = (
    Iterable[Request] | Generator[Request, None, None] | AsyncGenerator[Request, None]
)
