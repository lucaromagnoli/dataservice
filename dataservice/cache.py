"""Cache Module."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from abc import ABC
from contextlib import nullcontext
from functools import wraps
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from anyio import to_thread

from dataservice import CacheConfig
from dataservice.models import Request, Response

logger = logging.getLogger(__name__)


class AsyncCache(ABC):
    """Abstract Async Cache Interface"""

    def __init__(self):
        self.cache = {}
        self.start_time = time.time()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.create_task(self.flush())
        )
        loop.add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(self.flush())
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush()

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

    async def load(self):
        raise NotImplementedError("Load function not provided")

    async def set(self, key: str, value: Any):
        self.cache[key] = value

    async def get(self, key: str) -> Any:
        return self.cache.get(key)

    async def delete(self, key):
        del self.cache[key]

    async def clear(self):
        self.cache.clear()

    async def flush(self):
        raise NotImplementedError("Save state callable not provided")

    async def write_periodically(self, interval: int):
        """Write the cache to disk periodically.

        :param interval: The interval in seconds to write the cache.
        """

        if time.time() - self.start_time >= interval:
            logger.debug(f"Writing cache to disk every at interval {interval}")
            await self.flush()
            self.start_time = time.time()


class LocalJsonCache(AsyncCache):
    """Simple JSON disk based cache implementation."""

    def __init__(self, path: Path):
        """Initialize the DictCache."""
        super().__init__()
        self.path = path
        self.cache = {}

    async def load(self):
        """Load cache data from a JSON file."""
        logger.debug("Loading cache from disk")

        def sync_load():
            with open(self.path) as f:
                self.cache = json.load(f)

        if self.path.exists():
            await to_thread.run_sync(sync_load)

    async def flush(self):
        """Save cache data to a JSON file."""
        logger.debug("Saving cache to disk")

        def sync_flush():
            with open(self.path, "w") as f:
                json.dump(self.cache, f)

        await to_thread.run_sync(sync_flush)


class RemoteCache(AsyncCache):
    """Generic implementation for Remote based storage."""

    def __init__(
        self,
        save_state: Optional[Callable[[dict], Awaitable[None]]] = None,
        load_state: Optional[Callable[[], Awaitable[dict]]] = None,
    ):
        """Initialize the ApifyCache."""
        super().__init__()
        self.save_state = save_state
        self.load_state = load_state

    async def load(self):
        """Load cache data from Remote."""
        logger.debug("Loading cache from Remote")
        self.cache = await self.load_state()

    async def flush(self):
        """Save cache data to Remote."""
        logger.debug("Saving cache to Remote")
        await self.save_state(self.cache)


async def cache_request(cache: AsyncCache) -> Callable:
    """
    Caches the raw values (text, data) of the Response object returned by the request function.

    :param cache: The cache to use.
    """

    async def wrapped_request(request: Request) -> Response:
        """
        Wraps a function to cache its results.

        :param request: The request to cache.
        """

        @wraps(wrapped_request)
        async def inner() -> Response:
            key = request.unique_key
            if key in cache:
                logger.debug(f"Cache hit for {key}")
                text, data = await cache.get(key)
                return Response(
                    request=request, text=text, data=data, url=request.url_encoded
                )
            else:
                logger.debug(f"Cache miss for {key}")
                response = await request.client(request)
                value = response.text, response.data
                await cache.set(key, value)
                return response

        return await inner()

    return wrapped_request


class CacheFactory:
    """Factory for creating cache instances."""

    def __init__(self, cache_config: CacheConfig):
        self.cache_config = cache_config

    async def init_cache(self) -> AsyncCache | nullcontext[Any]:
        """Create a cache instance based on the cache config."""
        if not self.cache_config.use:
            logger.debug("Cache disabled")
            return nullcontext()
        if self.cache_config.cache_type == "local":
            logger.debug("Using local cache")
            cache = LocalJsonCache(Path(self.cache_config.path))
        elif self.cache_config.cache_type == "remote":
            logger.debug("Using remote cache")
            cache = RemoteCache(  # type: ignore
                save_state=self.cache_config.save_state,
                load_state=self.cache_config.load_state,
            )
        else:
            # This should never happen as CacheConfig enforces the cache type
            raise ValueError("Invalid cache type")
        await cache.load()
        return cache
