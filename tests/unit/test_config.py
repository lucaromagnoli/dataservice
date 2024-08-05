import pytest
from pydantic import ValidationError

from config import RetryConfig
from dataservice import ServiceConfig


def test_retry_config_defaults():
    config = RetryConfig()
    assert config.max_attempts == 3
    assert config.wait_exp_max == 10
    assert config.wait_exp_min == 4
    assert config.wait_exp_mul == 1


def test_retry_config_custom_values():
    config = RetryConfig(
        max_attempts=5, wait_exp_max=15, wait_exp_min=5, wait_exp_mul=2
    )
    assert config.max_attempts == 5
    assert config.wait_exp_max == 15
    assert config.wait_exp_min == 5
    assert config.wait_exp_mul == 2


def test_retry_config_invalid_values():
    with pytest.raises(ValidationError):
        RetryConfig(max_attempts=-1)
    with pytest.raises(ValidationError):
        RetryConfig(wait_exp_max=-1)
    with pytest.raises(ValidationError):
        RetryConfig(wait_exp_min=-1)
    with pytest.raises(ValidationError):
        RetryConfig(wait_exp_mul=-1)


def test_service_config_defaults():
    config = ServiceConfig()
    assert config.deduplication is True
    assert config.max_concurrency == 10
    assert config.random_delay == 0
    assert config.retry.max_attempts == 3


def test_service_config_custom_values():
    retry_config = {"max_attempts": 5}
    config = ServiceConfig(
        **{
            "deduplication": False,
            "max_concurrency": 20,
            "random_delay": 100,
            "retry": retry_config,
        }
    )
    assert config.deduplication is False
    assert config.max_concurrency == 20
    assert config.random_delay == 100
    assert config.retry.max_attempts == 5


def test_service_config_invalid_values():
    with pytest.raises(ValidationError):
        ServiceConfig(max_concurrency=-1)
    with pytest.raises(ValidationError):
        ServiceConfig(random_delay=-1)
