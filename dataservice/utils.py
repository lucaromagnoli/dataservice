import asyncio
from typing import Any, Callable, Coroutine, TypeVar

Nothing = TypeVar("Nothing")


def async_to_sync(
    coro: Callable[[Any], Coroutine[Any, Any, Nothing]], *args, **kwargs
) -> Any:
    """Run an async function synchronously. Wrapper around asyncio.run."""
    return asyncio.run(coro(*args, **kwargs))
