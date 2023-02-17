import asyncio

from typing import Callable, Any, Coroutine, TypeVar

Nothing = TypeVar("Nothing")


def async_to_sync(
    coro: Callable[[Any], Coroutine[Any, Any, Nothing]], *args, **kwargs
) -> Any:
    return asyncio.run(coro(*args, **kwargs))
