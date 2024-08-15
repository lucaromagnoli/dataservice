"""Cache Module."""

from __future__ import annotations

import atexit
import json
import logging
import time
from abc import ABC
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from dataservice.models import Request, Response

logger = logging.getLogger(__name__)


class Cache(ABC):
    """Base class for cache implementations."""

    def set(self, key: Any, value: Any) -> None:
        """Set a value in the cache."""
        raise NotImplementedError

    def get(self, key: Any) -> Any:
        """Get a value from the cache."""
        raise NotImplementedError

    def delete(self, key: Any) -> None:
        """Delete a value from the cache."""
        raise NotImplementedError

    def clear(self) -> None:
        """Clear the cache."""
        raise NotImplementedError


class JsonCache:
    """Simple JSON disk based cache implementation."""

    def __init__(self, path: Path):
        """Initialize the DictCache."""
        self.path = path
        self.cache = self._init_cache()
        self.start_time = time.time()
        atexit.register(self.write)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write()

    def _init_cache(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                return json.load(f)
        return {}

    def set(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache.get(key)

    def delete(self, key):
        del self.cache[key]

    def clear(self):
        self.cache.clear()

    def write(self):
        logger.info(f"Writing cache to {self.path}")
        with open(self.path, "w") as f:
            json.dump(self.cache, f)

    def write_periodically(self, interval):
        if time.time() - self.start_time >= interval.total_seconds():
            self.write()
            self.start_time = time.time()

    def __contains__(self, key):
        return key in self.cache

    def __len__(self):
        return len(self.cache)

    def __iter__(self):
        return iter(self.cache)

    def __repr__(self):
        return repr(self.cache)

    def __str__(self):
        return str(self.cache)


def cache_request(cache: Cache) -> Callable:
    """
    Caches the raw values (text, data) of the Response object returned by the request function.

    :param cache: The cache to use.
    """

    async def wrapper(req_func: Callable, request: Request) -> Response:
        """
        Wraps a function to cache its results.

        :param req_func: The function to wrap.
        :param request: The request to cache.
        """

        @wraps(req_func)
        async def inner() -> Response:
            key = request.url
            if key in cache:
                logger.debug(f"Cache hit for {key}")
                text, data = cache.get(key)
                return Response(request=request, text=text, data=data)
            else:
                logger.debug(f"Cache miss for {key}")
                response = await req_func(request)
                value = response.text, response.data
                cache.set(key, value)
                return response

        return await inner()

    return wrapper
