"""Tunnel health helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.telegram.miniapp.bootstrap import probe_local_health, probe_tunnel_health
from app.telegram.runtime_status import (
    get_telegram_runtime_status,
    is_mini_app_online,
    set_tunnel_reachable,
    set_tunnel_status,
)


def test_probe_tunnel_health_ok() -> None:
    response = MagicMock()
    response.status = 200
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    with patch("app.telegram.miniapp.bootstrap.urllib.request.urlopen", return_value=response):
        assert probe_tunnel_health("https://example.trycloudflare.com") is True


def test_probe_tunnel_health_fail() -> None:
    with patch(
        "app.telegram.miniapp.bootstrap.urllib.request.urlopen",
        side_effect=OSError("offline"),
    ):
        assert probe_tunnel_health("https://example.trycloudflare.com", attempts=1) is False


def test_probe_tunnel_health_retries() -> None:
    response = MagicMock()
    response.status = 200
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    side_effects = [OSError("wait"), response]
    with patch(
        "app.telegram.miniapp.bootstrap.urllib.request.urlopen",
        side_effect=side_effects,
    ), patch("app.telegram.miniapp.bootstrap.time.sleep"):
        assert probe_tunnel_health("https://example.trycloudflare.com", attempts=2, delay=0) is True


def test_probe_local_health() -> None:
    response = MagicMock()
    response.status = 200
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    with patch("app.telegram.miniapp.bootstrap.urllib.request.urlopen", return_value=response):
        assert probe_local_health() is True


def test_is_mini_app_online_requires_reachable_url() -> None:
    set_tunnel_status("ok", "https://example.trycloudflare.com")
    set_tunnel_reachable(False)
    assert is_mini_app_online() is False
    set_tunnel_reachable(True)
    assert is_mini_app_online() is True
    assert get_telegram_runtime_status().mini_url == "https://example.trycloudflare.com"
