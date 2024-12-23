"""Config."""

from __future__ import annotations

import random
from typing import Annotated, Any, Awaitable, Callable, Literal, NewType, Optional

from annotated_types import Ge
from pydantic import BaseModel, Field, FilePath, NewPath, model_validator

PositiveInt = Annotated[int, Ge(0)]
Milliseconds = NewType("Milliseconds", PositiveInt)
Seconds = NewType("Seconds", PositiveInt)


class RetryConfig(BaseModel):
    """Retry configuration for the service."""

    max_attempts: PositiveInt = 3
    wait_exp_max: PositiveInt = 10
    wait_exp_min: PositiveInt = 4
    wait_exp_mul: PositiveInt = 1


class RateLimiterConfig(BaseModel):
    """Retry configuration for the service."""

    max_rate: PositiveInt = 10
    time_period: Seconds = Seconds(60)


class CacheConfig(BaseModel):
    use: bool = Field(default=False, description="Whether to cache requests.")
    cache_type: Literal["json", "pickle", "remote"] = Field(
        default="json", description="The type of cache to use."
    )
    path: FilePath | NewPath = Field(
        default="cache.json",
        description="The path of the file to use for the cache. Defaults to 'cache.json'. Unused for remote cache.",
    )
    write_interval: PositiveInt = Field(
        default=20 * 60,
        description="The interval to write the cache in seconds. Defaults to 20 minutes.",
    )
    write_periodically: bool = Field(
        default=True,
        description="Whether to write the cache to disk periodically. Defaults to True.",
    )
    save_state: Optional[Callable[[dict], Awaitable[None]]] = Field(
        description="A function to save the cache state. Only used for remote cache.",
        default=None,
    )
    load_state: Optional[Callable[[], Awaitable[Any]]] = Field(
        description="A function to load the cache state. Only used for remote cache.",
        default=None,
    )

    @model_validator(mode="after")
    def validate(self) -> CacheConfig:  # type: ignore
        if self.cache_type == "remote" and not self.save_state and not self.load_state:
            raise ValueError(
                "Remote cache requires save_state and load_state functions."
            )
        if self.cache_type == "json" and str(self.path).split(".")[1] not in (
            "json",
            "jsonl",
            "json.gz",
        ):
            raise ValueError("JSON cache requires a .json file.")
        if self.cache_type == "pickle" and str(self.path).split(".")[1] not in (
            "pkl",
            "pickle",
        ):
            raise ValueError("Pickle cache requires a .pkl file.")
        return self


class DelayConfig(BaseModel):
    """Delay configuration for the service."""

    amount: Milliseconds = Field(
        default=Milliseconds(0),
        description="The total amount of delay in milliseconds.",
    )

    type: Literal["constant", "random"] = Field(
        default="random",
        description="The type of delay. Either constant or random. Defaults to random.",
    )

    def get(self):
        if self.type == "constant":
            return self.amount / 1000
        return random.randint(0, self.amount) / 1000


class ServiceConfig(BaseModel):
    """Global configuration for the service."""

    retry: RetryConfig = Field(
        default_factory=RetryConfig, description="The retry configuration."
    )
    deduplication: bool = Field(
        default=True, description="Whether to deduplicate requests."
    )
    max_concurrency: PositiveInt = Field(
        default=10, description="The maximum number of concurrent requests."
    )

    limiter: RateLimiterConfig | None = Field(
        description="The rate limiter configuration", default=None
    )
    cache: CacheConfig = Field(
        description="The cache configuration", default_factory=CacheConfig
    )
    delay: DelayConfig = Field(
        description="The delay configuration", default_factory=DelayConfig
    )


class ProxyConfig(BaseModel):
    """Proxy configuration for the service."""

    host: str = Field(description="The proxy host.")
    port: int = Field(description="The proxy port.")
    username: Optional[str] = Field(description="The proxy username.", default=None)
    password: Optional[str] = Field(description="The proxy password.", default=None)

    @classmethod
    def from_url(cls, url: str) -> ProxyConfig:
        if "://" in url:
            url = url.split("://")[1]
        if "@" in url:
            auth, url = url.split("@")
            username, password = auth.split(":")
        else:
            username = None
            password = None
        host, port = url.split(":")
        return cls(host=host, port=int(port), username=username, password=password)

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


class PlaywrightConfig(BaseModel):
    browser: Literal["chromium", "firefox", "webkit"] = Field(
        description="The browser to use.", default="chromium"
    )
    headless: bool = Field(description="Whether to run in headless mode.", default=True)
    slow_mo: PositiveInt = Field(
        description="The slow motion delay in milliseconds.", default=0
    )
    device: Optional[dict[str, Any]] = Field(
        description="The devices to use.", default=None
    )
