from pydantic import BaseModel


class ServiceConfig(BaseModel):
    max_workers: int = 10
    max_retries: int = 5
    wait_exponential_multiplier: int = 1
    wait_exponential_min: int = 4
    wait_exponential_max: int = 10
    deduplication: bool = True
