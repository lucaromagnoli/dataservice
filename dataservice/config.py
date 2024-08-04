from pydantic import BaseModel


class ServiceConfig(BaseModel):
    max_workers: int = 10
    deduplication: bool = True
    max_retries: int = 3
    wait_exp_mul: int = 1
    wait_exp_min: int = 4
    wait_exp_max: int = 10
