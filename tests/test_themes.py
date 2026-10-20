import pytest

from app import themes
from app.demos import active_demo
from app.main import app


def test_grocery_uses_fresh_market_by_default(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    monkeypatch.delenv("DEMO_THEME", raising=False)
    client = app.test_client()

    for path in ("/", "/story", "/accuracy"):
        page = client.get(path).data
        assert b"--canvas: #f6f4ec" in page or b"--slide-bg: #fbf8f1" in page, path


def test_theme_can_be_switched_by_query_cookie_and_env(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    client = app.test_client()

    night = client.get("/story?theme=lakehouse-night").data
    assert b"--slide-bg: #fbf8f1" not in night
    assert b'content="#0a1014"' in night

    client.set_cookie("theme", "lakehouse-night")
    assert b"--canvas: #f6f4ec" not in client.get("/").data

    monkeypatch.setenv("DEMO_THEME", "lakehouse-night")
    assert b"--canvas: #f6f4ec" not in app.test_client().get("/").data


def test_unknown_theme_falls_back_to_default():
    assert themes.resolve("neon") == themes.DEFAULT_THEME
    assert "</style><script>" not in themes.head_tags("fresh-market", "app")


def test_every_theme_defines_both_surfaces():
    for theme in themes.THEMES.values():
        assert {"app", "deck"} <= set(theme)
        assert {"app", "deck"} == set(theme["theme_color"])


def test_unknown_demo_is_rejected(monkeypatch):
    monkeypatch.setenv("DEMO", "nope")
    with pytest.raises(ValueError):
        active_demo()
