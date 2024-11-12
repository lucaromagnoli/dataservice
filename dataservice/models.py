"""Models for the data service."""

from __future__ import annotations

import urllib.parse
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Iterator,
    Literal,
    Optional,
    TypedDict,
    Union,
)

from bs4 import BeautifulSoup
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_serializer,
    model_validator,
)

from dataservice._utils import _get_func_name
from dataservice.config import ProxyConfig

GenericDataItem = dict[Any, Any] | BaseModel
RequestOrData = Union["Request", GenericDataItem]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
ClientCallable = Callable[["Request"], Awaitable["Response"]]
StrOrDict = str | dict


class Request(BaseModel):
    """Request model."""

    url: Annotated[
        HttpUrl, AfterValidator(str), Field(description="The URL of the request.")
    ]
    callback: CallbackType = Field(
        description="The callback function to process the response."
    )
    client: ClientCallable = Field(
        description="The client callable to use for the request."
    )
    method: Literal["GET", "POST"] = Field(
        description="The method of the request.", default="GET"
    )
    content_type: Literal["text", "json"] = Field(
        description="The content type of the request.", default="text"
    )
    headers: Optional[dict] = Field(
        description="The headers of the request.", default=None
    )
    cookies: Optional[list[dict]] = Field(
        description="The cookies of the request.", default=None
    )
    params: Optional[dict] = Field(
        description="The parameters of the request.", default=None
    )
    form_data: Optional[dict] = Field(
        description="The form data of the request.", default=None
    )
    json_data: Optional[dict] = Field(
        description="The json data of the request.", default=None
    )
    proxy: Optional[ProxyConfig] = Field(
        description="The proxy configuration for the request.", default=None
    )
    timeout: int = Field(
        description="The time out of the request.", default=30, ge=1, le=300
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate(self) -> Request:  # type: ignore
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

    @property
    def callback_name(self) -> str:
        return _get_func_name(self.callback)

    @property
    def client_name(self) -> str:
        return _get_func_name(self.client)

    @property
    def unique_key(self) -> str:
        """Return a unique key for the request."""
        key = f"{self.method} {self.url}"
        if self.params:
            key += f" {self.params}"
        if self.form_data:
            key += f" {self.form_data}"
        if self.json_data:
            key += f" {self.json_data}"
        return key

    @property
    def url_encoded(self) -> HttpUrl:
        """Return the URL encoded."""
        url = str(self.url)
        if "?" in url or not self.params:
            return HttpUrl(url)

        if url.endswith("/"):
            url = url[:-1]
        return HttpUrl(f"{url}?{urllib.parse.urlencode(self.params)}")  # type: ignore


class Response(BaseModel):
    """Response model."""

    request: Request = Field(description="The request that generated the response.")
    url: Annotated[
        HttpUrl, AfterValidator(str), Field(description="The URL of the response.")
    ]
    status_code: int = Field(
        description="The status code of the response.", default=200, ge=100, le=599
    )
    headers: Optional[dict] = Field(
        description="The headers of the response.", default=None
    )
    cookies: Optional[list[dict]] = Field(
        description="The cookies of the response.", default=None
    )
    text: str = Field(description="The text of the response.", default="")
    data: dict | None = Field(description="The data of the response.", default=None)
    __html: BeautifulSoup | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def client(self) -> ClientCallable:
        return self.request.client

    @property
    def html(self) -> BeautifulSoup:
        """Return the BeautifulSoup object of the response, if the initial request asked for text data."""
        if self.request.content_type == "json":
            raise ValueError(
                "Cannot create BeautifulSoup object when the Request content type is JSON."
            )
        if self.__html is None:
            self.__html = BeautifulSoup(self.text, "html5lib")
        return self.__html


class FailedRequest(TypedDict):
    """Failed request model."""

    request: Request
    message: str
    exception: str
