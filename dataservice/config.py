from typing import Annotated, NewType

from annotated_types import Ge
from pydantic import BaseModel, Field

PositiveInt = Annotated[int, Ge(0)]
Milliseconds = NewType("Milliseconds", PositiveInt)


class RetryConfig(BaseModel):
    """Retry configuration for the service."""

    max_attempts: PositiveInt = 3
    wait_exp_max: PositiveInt = 10
    wait_exp_min: PositiveInt = 4
    wait_exp_mul: PositiveInt = 1


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
    random_delay: Milliseconds = Field(
        default=Milliseconds(0),
        description="The maximum random delay between requests.",
    )

    cache: bool = Field(default=False, description="Whether to cache requests.")
    cache_name: str = Field(
        default="cache", description="A name to use for the cache. Defaults to 'cache'."
    )
