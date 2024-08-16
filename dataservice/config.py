"""Config."""

from typing import Annotated, NewType

from annotated_types import Ge
from pydantic import BaseModel, Field, NewPath

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
    path: NewPath = Field(
        default="cache.json",
        description="The path of the file to use for the cache. Defaults to 'cache.json'.",
    )
    write_interval: PositiveInt = Field(
        default=20 * 60,
        description="The interval to write the cache in seconds.Defaults to 20 minutes.",
    )


class ServiceConfig(BaseModel):
    """Global configuration for the service."""

    retry: RetryConfig = Field(
        default_factory=RetryConfig, description="The retry configuration."
    )
    deduplication: bool = Field(
        default=True, description="Whether to deduplicate requests."
    )
    deduplication_keys: set[str] = Field(
        default={
            "url",
            "params",
            "method",
            "form_data",
            "json_data",
            "content_type",
            "headers",
        },
        description="A list of keys to use for deduplication.",
    )
    max_concurrency: PositiveInt = Field(
        default=10, description="The maximum number of concurrent requests."
    )
    random_delay: Milliseconds = Field(
        default=Milliseconds(0),
        description="The maximum random delay between requests.",
    )

    constant_delay: Milliseconds = Field(
        default=Milliseconds(0),
        description="Constant delay between requests.",
    )

    limiter: RateLimiterConfig | None = Field(
        description="The rate limiter configuration", default=None
    )
    cache: CacheConfig = Field(
        description="The cache configuration", default_factory=CacheConfig
    )
