from pydantic import BaseModel


class ServiceConfig(BaseModel):
    deduplication: bool = True
    max_retries: int = 3
    wait_exp_max: int = 10
    wait_exp_min: int = 4
    wait_exp_mul: int = 1
