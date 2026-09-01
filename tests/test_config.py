"""Settings parsing — the bits that bite during deployment."""

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://portal.example", ["https://portal.example"]),
        ("https://a.example,https://b.example", ["https://a.example", "https://b.example"]),
        ("https://a.example, https://b.example", ["https://a.example", "https://b.example"]),
        ('["https://a.example","https://b.example"]', ["https://a.example", "https://b.example"]),
        ("*", ["*"]),
    ],
)
def test_cors_origins_accepts_dashboard_and_json_forms(monkeypatch, value, expected):
    """A hosting dashboard invites a bare comma-separated string; JSON must
    keep working too. Getting this wrong is a crash loop, not a 500."""
    monkeypatch.setenv("CVBIO_CORS_ORIGINS", value)
    assert Settings().cors_origins == expected


def test_cors_origins_defaults_to_wildcard(monkeypatch):
    monkeypatch.delenv("CVBIO_CORS_ORIGINS", raising=False)
    assert Settings().cors_origins == ["*"]


def test_protected_planet_token_is_optional(monkeypatch):
    monkeypatch.delenv("CVBIO_PROTECTED_PLANET_TOKEN", raising=False)
    assert Settings().protected_planet_token is None
