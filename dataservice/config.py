from typing import Annotated, NewType

from annotated_types import Ge
from pydantic import BaseModel

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

    deduplication: bool = True
    max_concurrency: PositiveInt = 10
    random_delay: Milliseconds = Milliseconds(0)
    retry: RetryConfig = RetryConfig()
