import pytest
from fastapi.testclient import TestClient

from app.cache import cache_clear
from app.main import app


@pytest.fixture
def client():
    cache_clear()
    with TestClient(app) as c:
        yield c
