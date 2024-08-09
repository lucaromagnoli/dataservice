import asyncio
import json
import logging
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
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
        self._cache = {}

    @property
    def cache(self):
        if not self._cache:
            try:
                with open(self.path, "r") as f:
                    self._cache = json.load(f)
            except FileNotFoundError:
                pass
        return self._cache

    @cache.setter
    def cache(self, value):
        self._cache = value

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


class AsyncJsonCache(JsonCache):
    """Simple Pickle disk based cache implementation."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.write()

    async def write(self):
        with ThreadPoolExecutor() as pool:
            await asyncio.get_event_loop().run_in_executor(pool, super().write)


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
