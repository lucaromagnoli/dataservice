from dataservice.clients import (
    PLAYWRIGHT_AVAILABLE,
    HttpXClient,
    PlaywrightClient,
    PlaywrightPage,
)
from dataservice.config import (
    CacheConfig,
    RateLimiterConfig,
    RetryConfig,
    ServiceConfig,
)
from dataservice.data import BaseDataItem, DataWrapper
from dataservice.exceptions import DataServiceException, RetryableException
from dataservice.logs import setup_logging
from dataservice.models import FailedRequest, Request, Response
from dataservice.service import AsyncDataService, DataService


def check_playwright_availability():
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError(
            "Playwright optional dependency is not installed. Please install it with `pip install python-dataservice[playwright]`."
        )


# Check availability when importing PlaywrightClient or PlaywrightPage
if "PlaywrightClient" in globals() or "PlaywrightPage" in globals():
    check_playwright_availability()


__all__ = [
    "AsyncDataService",
    "BaseDataItem",
    "CacheConfig",
    "DataService",
    "DataServiceException",
    "DataWrapper",
    "FailedRequest",
    "HttpXClient",
    "PlaywrightClient",
    "PlaywrightPage",
    "RateLimiterConfig",
    "Request",
    "Response",
    "RetryableException",
    "RetryConfig",
    "ServiceConfig",
    "setup_logging",
]
