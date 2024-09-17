from dataservice.clients import HttpXClient
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
from dataservice.service import DataService
import importlib.metadata

__all__ = [
    "BaseDataItem",
    "DataService",
    "DataWrapper",
    "HttpXClient",
    "Request",
    "Response",
    "FailedRequest",
    "DataServiceException",
    "RetryableException",
    "ServiceConfig",
    "CacheConfig",
    "RateLimiterConfig",
    "RetryConfig",
    "setup_logging",
]

__version__ = importlib.metadata.version("python-dataservice")
