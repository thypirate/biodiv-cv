import os

# Settings are read at import time; the suite never needs a real Redis.
os.environ.setdefault("CVBIO_REDIS_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from app.cache import cache_clear
from app.main import app
from app.rate_limiter import limiter


@pytest.fixture
def client():
    cache_clear()
    limiter.reset()
    with TestClient(app) as c:
        yield c
