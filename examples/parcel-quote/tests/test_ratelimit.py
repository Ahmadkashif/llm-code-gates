import pytest

from quotesvc.ratelimit import TokenBucket


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_burst_then_refill():
    c = Clock()
    b = TokenBucket(rate_per_s=1, burst=2, clock=c)
    assert b.allow("a") and b.allow("a")
    assert not b.allow("a")
    c.t = 1.0
    assert b.allow("a")
    assert not b.allow("a")


def test_clients_are_independent():
    b = TokenBucket(rate_per_s=1, burst=1, clock=Clock())
    assert b.allow("a")
    assert b.allow("b")
    assert not b.allow("a")


def test_invalid_config():
    with pytest.raises(ValueError):
        TokenBucket(0, 1)
    with pytest.raises(ValueError):
        TokenBucket(1, 0)
