from ask.cache import TTLCache


def test_get_returns_none_for_missing_key():
    cache = TTLCache(ttl_seconds=60, clock=lambda: 0.0)
    assert cache.get("missing") is None


def test_set_then_get_returns_value_within_ttl():
    cache = TTLCache(ttl_seconds=60, clock=lambda: 0.0)
    cache.set("key", {"answer": 42})
    assert cache.get("key") == {"answer": 42}


def test_get_returns_none_after_ttl_expires():
    times = iter([0.0, 0.0, 61.0])
    cache = TTLCache(ttl_seconds=60, clock=lambda: next(times))
    cache.set("key", "value")
    assert cache.get("key") == "value"
    assert cache.get("key") is None
