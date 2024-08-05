from contextlib import nullcontext as does_not_raise

import pytest
from bs4 import BeautifulSoup
from pydantic import ValidationError

from dataservice.config import RetryConfig, ServiceConfig
from dataservice.models import Request, Response
from tests.unit.conftest import ToyClient


@pytest.fixture
def dummy_callback() -> None:
    def inner():
        pass

    return inner


@pytest.fixture
def valid_url():
    return "https://example.com/"


@pytest.fixture
def valid_request(valid_url, dummy_callback):
    return Request(url=valid_url, callback=dummy_callback, client=ToyClient())


def test_request_creation(valid_url, dummy_callback):
    request = Request(url=valid_url, callback=dummy_callback, client=ToyClient())
    assert request.url == valid_url
    assert request.callback == dummy_callback
    assert request.method == "GET"
    assert request.headers is None
    assert request.params is None
    assert request.form_data is None
    assert request.json_data is None
    assert request.content_type == "text"
    assert isinstance(request.client, ToyClient)


def test_request_optional_fields(valid_url, dummy_callback):
    headers = {"User-Agent": "pytest"}
    params = {"q": "test"}
    data = {"key": "value"}
    json_data = {"json_key": "json_value"}
    request = Request(
        url=valid_url,
        callback=dummy_callback,
        method="POST",
        headers=headers,
        params=params,
        form_data=data,
        json_data=json_data,
        content_type="json",
        client=ToyClient(),
    )
    assert request.method == "POST"
    assert request.headers == headers
    assert request.params == params
    assert request.form_data == data
    assert request.json_data == json_data
    assert request.content_type == "json"
    assert isinstance(request.client, ToyClient)


def test_response_creation(valid_request):
    data = "<html></html>"
    response = Response(request=valid_request, data=data)
    assert response.request == valid_request
    assert response.data == data


def test_response_soup_property(valid_request):
    html_data = "<html><body><p>Hello, world!</p></body></html>"
    response = Response(request=valid_request, data=html_data)
    assert isinstance(response.soup, BeautifulSoup)
    assert response.soup.find("p").text == "Hello, world!"


def test_response_soup_property_with_dict(valid_request):
    json_data = {"key": "value"}
    response = Response(request=valid_request, data=json_data)
    with pytest.raises(Warning, match="Cannot create BeautifulSoup from dict."):
        _ = response.soup


@pytest.mark.parametrize(
    "url, method, content_type, headers, params, form_data, json_data, client, context",
    [
        (
            "http://example.com",
            "GET",
            "text",
            None,
            None,
            None,
            None,
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "GET",
            "text",
            None,
            None,
            {"key": "value"},
            None,
            ToyClient(),
            pytest.raises(ValidationError),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            {"key": "value"},
            None,
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            None,
            {"key": "value"},
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            None,
            None,
            "TestClient",
            pytest.raises(ValidationError),
        ),
        (
            "http://example.com",
            "POST",
            "json",
            None,
            None,
            None,
            None,
            "TestClient",
            pytest.raises(ValidationError),
        ),
    ],
)
def test_request_validation(
    url, method, content_type, headers, params, form_data, json_data, client, context
):
    with context:
        request = Request(
            url=url,
            callback=lambda x: x,
            method=method,
            content_type=content_type,
            headers=headers,
            params=params,
            form_data=form_data,
            json_data=json_data,
            client=client,
        )
        assert request


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
    retry_config = RetryConfig(max_attempts=5)
    config = ServiceConfig(
        deduplication=False, max_concurrency=20, random_delay=100, retry=retry_config
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
