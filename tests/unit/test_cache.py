import time

import pytest

from dataservice import CacheConfig
from dataservice.cache import CacheFactory, JsonCache, PickleCache, RemoteCache


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_initialization_creates_empty_cache(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    assert len(cache) == 0


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_initialization_loads_existing_cache(tmp_path, ext, CacheType):
    cache_file = tmp_path / f"cache.{ext}"
    if ext == "json":
        cache_file.write_text('{"key": "value"}')
    else:
        cache_file.write_bytes(
            b"\x80\x04\x95\x12\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x03key\x94\x8c\x05value\x94s."
        )
    cache = CacheType(cache_file)
    await cache.load()
    assert await cache.get("key") == "value"


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_set_and_get_value(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    await cache.set("key", "value")
    assert await cache.get("key") == "value"


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_delete_value(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.set("key", "value")
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_clear_all_values(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.clear()
    assert len(cache) == 0


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_flush_persists_data(tmp_path, ext, CacheType):
    cache_file = tmp_path / f"cache.{ext}"
    cache = CacheType(cache_file)
    await cache.load()
    await cache.set("key", "value")
    await cache.flush()
    new_cache = CacheType(cache_file)
    await new_cache.load()
    assert await new_cache.get("key") == "value"


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_contains_key(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    await cache.set("key", "value")
    assert "key" in cache


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_length(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    assert len(cache) == 2


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_cache_iteration(tmp_path, ext, CacheType):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    keys = list(iter(cache))
    assert keys == ["key1", "key2"]


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_write_periodically_writes_when_interval_passed(
    tmp_path, mocker, ext, CacheType
):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    cache.start_time = time.time() - 3600  # Simulate 1 hour has passed
    await cache.set("key", "value")
    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())
    await cache.write_periodically(1800)
    mock_flush.assert_awaited_once()


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_write_periodically_does_not_write_when_interval_not_passed(
    tmp_path, mocker, ext, CacheType
):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    cache.start_time = time.time()  # No time has passed
    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())
    await cache.set("key", "value")
    await cache.write_periodically(1800)
    mock_flush.assert_not_awaited()


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_write_periodically_resets_start_time_after_writing(
    tmp_path, mocker, ext, CacheType
):
    cache = CacheType(tmp_path / f"cache.{ext}")
    cache.start_time = time.time() - 3600  # Simulate 1 hour has passed

    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())
    await cache.set("key", "value")
    # Call the method and check if `write` was awaited
    await cache.write_periodically(1800)
    mock_flush.assert_awaited_once()  # Ensure `write` was called as expected

    # Verify that `start_time` has been reset correctly
    assert abs(cache.start_time - time.time()) < 1


@pytest.mark.parametrize("ext, CacheType", [("json", JsonCache), ("pkl", PickleCache)])
@pytest.mark.asyncio
async def test_write_periodically_doesnt_write_on_no_writes_yet(
    tmp_path, mocker, ext, CacheType
):
    cache = CacheType(tmp_path / f"cache.{ext}")
    await cache.load()
    cache.has_written = False
    cache.start_time = time.time() - 1

    mock_sync_flush = mocker.patch.object(cache, "sync_flush")
    await cache.write_periodically(1)

    assert mock_sync_flush.call_count == 0  # Ensure `sync_flush` was not called


@pytest.mark.parametrize(
    "ext, type_name, CacheType",
    [("json", "json", JsonCache), ("pkl", "pickle", PickleCache)],
)
@pytest.mark.asyncio
async def test_cache_factory_init_cache(tmp_path, ext, type_name, CacheType):
    cache_file = tmp_path / f"cache.{ext}"
    if ext == "json":
        cache_file.write_text('{"key": "value"}')
    else:
        cache_file.write_bytes(
            b"\x80\x04\x95\x12\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x03key\x94\x8c\x05value\x94s."
        )
    cache_config = CacheConfig(
        cache_type=type_name, path=tmp_path / f"cache.{ext}", use=True
    )
    factory = CacheFactory(cache_config)
    cache = await factory.init_cache()
    assert isinstance(cache, CacheType)
    assert await cache.get("key") == "value"


@pytest.mark.asyncio
async def test_cache_factory_init_remote_cache(mocker):
    cache_config = CacheConfig(
        use=True,
        cache_type="remote",
        save_state=mocker.AsyncMock(),
        load_state=mocker.AsyncMock(return_value={"key": "value"}),
    )
    factory = CacheFactory(cache_config)
    cache = await factory.init_cache()
    assert isinstance(cache, RemoteCache)
    assert await cache.get("key") == "value"
