import asyncio


class AsyncIterator:
    def __init__(self):
        self.index = -1

    def __aiter__(self):
        """Return the data service as an async iterator."""
        return self

    async def __anext__(self):
        """Return the next item from the data service."""
        items = [i async for i in self.fetch()]
        self.index += 1
        if self.index >= len(items):
            raise StopAsyncIteration
        return items[self.index]

    async def fetch(self):
        for i in range(20):
            print(f"Yielding {i}")
            yield i


async def main():
    async_iterator = AsyncIterator()
    items_from_fetch = [i async for i in async_iterator.fetch()]

    async_iterator = AsyncIterator()
    items_from_self = [i async for i in async_iterator]
    print(f"Items from fetch {len(items_from_fetch)}")
    print(f"Items from self {len(items_from_self)}")

if __name__ == "__main__":
    asyncio.run(main())