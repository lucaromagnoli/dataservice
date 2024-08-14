from dataservice.cache import JsonCache


def cache_initialization_creates_empty_cache(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    assert len(cache) == 0


def test_cache_initialization_loads_existing_cache(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"key": "value"}')
    cache = JsonCache(cache_file)
    assert cache.get("key") == "value"


def test_cache_set_and_get_value(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_cache_delete_value(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key", "value")
    cache.delete("key")
    assert cache.get("key") is None


def test_cache_clear_all_values(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert len(cache) == 0


def test_cache_write_persists_data(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache = JsonCache(cache_file)
    cache.set("key", "value")
    cache.write()
    new_cache = JsonCache(cache_file)
    assert new_cache.get("key") == "value"


def test_cache_contains_key(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key", "value")
    assert "key" in cache


def test_cache_length(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    assert len(cache) == 2


def test_cache_iteration(tmp_path):
    cache = JsonCache(tmp_path / "cache.json")
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    keys = list(iter(cache))
    assert keys == ["key1", "key2"]
