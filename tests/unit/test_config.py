import json
import os
import pickle

import pytest
from pydantic import ValidationError

from dataservice import CacheConfig
from dataservice.config import ProxyConfig, RetryConfig, ServiceConfig


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
    assert config.delay.amount == 0.0
    assert config.retry.max_attempts == 3


def test_service_config_custom_values():
    retry_config = {"max_attempts": 5}
    config = ServiceConfig(
        **{
            "deduplication": False,
            "max_concurrency": 20,
            "delay": {"amount": 1000},
            "retry": retry_config,
        }
    )
    assert config.deduplication is False
    assert config.max_concurrency == 20
    assert config.delay.amount == 1000
    assert config.retry.max_attempts == 5


def test_service_config_invalid_values():
    with pytest.raises(ValidationError):
        ServiceConfig(max_concurrency=-1)
    with pytest.raises(ValidationError):
        ServiceConfig(delay={"amount": -1})


@pytest.fixture
def cache_path(tmp_path, request):
    cache_path = tmp_path / request.param
    if request.param.endswith(".json"):
        with open(cache_path, "w") as f:
            json.dump({"foo": "bar"}, f)
    else:
        with open(cache_path, "wb") as f:
            pickle.dump({"foo": "bar"}, f)
    yield cache_path
    os.remove(cache_path)


@pytest.mark.parametrize("cache_path", ["cache.json", "cache.pkl"], indirect=True)
def test_cache_config_write(cache_path):
    cache_type = "json" if cache_path.suffix == ".json" else "pickle"
    ServiceConfig(cache=CacheConfig(path=cache_path, use=True, cache_type=cache_type))


@pytest.mark.parametrize(
    "url, expected_host, expected_port, expected_username, expected_password",
    [
        ("http://localhost:8080", "localhost", 8080, None, None),
        ("http://user:pass@localhost:8080", "localhost", 8080, "user", "pass"),
        ("http://localhost:8080", "localhost", 8080, None, None),
        ("http://user:pass@127.0.0.1:3128", "127.0.0.1", 3128, "user", "pass"),
    ],
)
def test_proxy_config_from_url(
    url, expected_host, expected_port, expected_username, expected_password
):
    proxy_config = ProxyConfig.from_url(url)
    assert proxy_config.host == expected_host
    assert proxy_config.port == expected_port
    assert proxy_config.username == expected_username
    assert proxy_config.password == expected_password
