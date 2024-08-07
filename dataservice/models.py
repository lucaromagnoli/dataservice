"""Models for the data service."""

from __future__ import annotations

from functools import partial
from typing import (
    Annotated,
    Any,
    Callable,
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
    Field,
    BaseModel,
    HttpUrl,
    model_serializer,
    model_validator,
    ConfigDict,
)

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
ClientCallable = Callable[["Request"], "Response"]
StrOrDict = str | dict


class ProxyConfig(BaseModel):
    """Proxy configuration for the service."""

    host: str = Field(description="The proxy host.")
    port: int = Field(description="The proxy port.")
    username: Optional[str] = Field(description="The proxy username.", default=None)
    password: Optional[str] = Field(description="The proxy password.", default=None)

    @property
    def proxy_url(self) -> str:
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


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

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    @property
    def callback_name(self) -> str:
        return self._get_func_name(self.callback)

    @property
    def client_name(self) -> str:
        return self._get_func_name(self.client)

    @staticmethod
    def _get_func_name(func: Callable):
        if isinstance(func, partial):
            if hasattr(func, "keywords"):
                # functools.wraps
                if "wrapped" in func.keywords:
                    return func.keywords["wrapped"].__name__
            return func.func.__name__
        elif hasattr(func, "__name__"):
            return func.__name__
        elif hasattr(func, "__class__"):
            return type(func).__name__
        else:
            return str(func)


class Response(BaseModel):
    """Response model."""

    request: Request = Field(description="The request that generated the response.")
    status_code: int = Field(
        description="The status code of the response.", default=200, ge=100, le=599
    )
    text: str = Field(description="The text of the response.", default="")
    data: dict | None = Field(description="The data of the response.", default=None)
    __html: BeautifulSoup | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
    error: str
