import time

import pytest

from dataservice import CacheConfig
from dataservice.cache import CacheFactory, LocalJsonCache, RemoteCache


@pytest.mark.anyio
async def test_cache_initialization_creates_empty_cache(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    assert len(cache) == 0


@pytest.mark.anyio
async def test_cache_initialization_loads_existing_cache(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"key": "value"}')
    cache = LocalJsonCache(cache_file)
    await cache.load()
    assert await cache.get("key") == "value"


@pytest.mark.anyio
async def test_cache_set_and_get_value(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    await cache.set("key", "value")
    assert await cache.get("key") == "value"


@pytest.mark.anyio
async def test_cache_delete_value(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.set("key", "value")
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.anyio
async def test_cache_clear_all_values(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.clear()
    assert len(cache) == 0


@pytest.mark.anyio
async def test_cache_flush_persists_data(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache = LocalJsonCache(cache_file)
    await cache.load()
    await cache.set("key", "value")
    await cache.flush()
    new_cache = LocalJsonCache(cache_file)
    await new_cache.load()
    assert await new_cache.get("key") == "value"


@pytest.mark.anyio
async def test_cache_contains_key(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    await cache.set("key", "value")
    assert "key" in cache


@pytest.mark.anyio
async def test_cache_length(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    assert len(cache) == 2


@pytest.mark.anyio
async def test_cache_iteration(tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    keys = list(iter(cache))
    assert keys == ["key1", "key2"]


@pytest.mark.anyio
async def test_write_periodically_writes_when_interval_passed(tmp_path, mocker):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    cache.start_time = time.time() - 3600  # Simulate 1 hour has passed
    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())
    await cache.write_periodically(1800)
    mock_flush.assert_awaited_once()


@pytest.mark.anyio
async def test_write_periodically_does_not_write_when_interval_not_passed(
    tmp_path, mocker
):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    cache.start_time = time.time()  # No time has passed
    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())
    await cache.write_periodically(1800)
    mock_flush.assert_not_awaited()


@pytest.mark.anyio
async def test_write_periodically_resets_start_time_after_writing(tmp_path, mocker):
    cache = LocalJsonCache(tmp_path / "cache.json")
    cache.start_time = time.time() - 3600  # Simulate 1 hour has passed

    mock_flush = mocker.patch.object(cache, "flush", mocker.AsyncMock())

    # Call the method and check if `write` was awaited
    await cache.write_periodically(1800)
    mock_flush.assert_awaited_once()  # Ensure `write` was called as expected

    # Verify that `start_time` has been reset correctly
    assert abs(cache.start_time - time.time()) < 1


@pytest.mark.anyio
async def test_cache_factory_creates_local_json_cache(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"key": "value"}')
    cache_config = CacheConfig(cache_type="local", path=tmp_path / "cache.json")
    factory = CacheFactory(cache_config)
    cache = await factory.create_cache()
    assert isinstance(cache, LocalJsonCache)
    assert await cache.get("key") == "value"


@pytest.mark.anyio
async def test_cache_factory_creates_remote_cache(mocker):
    cache_config = CacheConfig(
        cache_type="remote",
        save_state=mocker.AsyncMock(),
        load_state=mocker.AsyncMock(return_value={"key": "value"}),
    )
    factory = CacheFactory(cache_config)
    cache = await factory.create_cache()
    assert isinstance(cache, RemoteCache)
    assert await cache.get("key") == "value"
