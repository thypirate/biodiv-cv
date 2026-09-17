import asyncio

from app.cache import cache_clear, cached


def test_cached_dedupes_concurrent_callers():
    calls = 0

    @cached(ttl=60)
    async def fetch(name: str) -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return name.upper()

    async def run():
        results = await asyncio.gather(*(fetch("gbif") for _ in range(10)))
        assert results == ["GBIF"] * 10
        # A second wave must be served entirely from the cache.
        await fetch("gbif")

    cache_clear()
    asyncio.run(run())
    assert calls == 1


def test_cached_separates_arguments():
    calls = 0

    @cached(ttl=60)
    async def fetch(key: int) -> int:
        nonlocal calls
        calls += 1
        return key * 2

    async def run():
        assert await fetch(1) == 2
        assert await fetch(2) == 4
        assert await fetch(1) == 2

    cache_clear()
    asyncio.run(run())
    assert calls == 2


def test_locks_are_released_after_use():
    """Every distinct key used to leave a lock behind forever."""

    @cached(ttl=60)
    async def fetch(i: int) -> int:
        await asyncio.sleep(0)
        return i

    async def run():
        # Distinct keys, plus concurrent callers sharing the same key.
        await asyncio.gather(*(fetch(i % 50) for i in range(500)))

    cache_clear()
    asyncio.run(run())
    assert fetch.cache_locks == {}


def test_lock_released_when_upstream_fails():
    @cached(ttl=60)
    async def boom(i: int) -> int:
        raise RuntimeError("upstream down")

    async def run():
        for i in range(20):
            try:
                await boom(i)
            except RuntimeError:
                pass

    cache_clear()
    asyncio.run(run())
    assert boom.cache_locks == {}
