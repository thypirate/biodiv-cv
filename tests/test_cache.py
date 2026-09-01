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
