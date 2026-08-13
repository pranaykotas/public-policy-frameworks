from ask.ratelimit import RateLimiter


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=lambda: 0.0)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True


def test_blocks_requests_over_the_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=lambda: 0.0)
    limiter.allow("client-a")
    limiter.allow("client-a")
    assert limiter.allow("client-a") is False


def test_different_clients_have_independent_limits():
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=lambda: 0.0)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True


def test_old_requests_expire_out_of_the_window():
    times = iter([0.0, 0.0, 61.0])
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=lambda: next(times))
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-a") is True
