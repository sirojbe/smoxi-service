"""Shared Telegram runtime status for the desktop status bar."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class TelegramRuntimeStatus:
    """Live bot / Mini App status shown in the shell."""

    bot: str = "checking"  # checking | ok | fail | no_token
    bot_detail: str = ""
    mini_url: str | None = None
    tunnel: str = "idle"  # idle | starting | ok | fail
    tunnel_detail: str = ""
    tunnel_reachable: bool = False


_lock = Lock()
_status = TelegramRuntimeStatus()


def get_telegram_runtime_status() -> TelegramRuntimeStatus:
    with _lock:
        return TelegramRuntimeStatus(
            bot=_status.bot,
            bot_detail=_status.bot_detail,
            mini_url=_status.mini_url,
            tunnel=_status.tunnel,
            tunnel_detail=_status.tunnel_detail,
            tunnel_reachable=_status.tunnel_reachable,
        )


def set_bot_status(state: str, detail: str = "") -> None:
    with _lock:
        _status.bot = state
        _status.bot_detail = detail


def set_tunnel_status(state: str, url: str | None = None, detail: str = "") -> None:
    with _lock:
        _status.tunnel = state
        _status.tunnel_detail = detail
        if url is not None:
            _status.mini_url = url or None
        if state != "ok":
            _status.tunnel_reachable = False


def set_tunnel_reachable(reachable: bool) -> None:
    with _lock:
        _status.tunnel_reachable = reachable


def is_mini_app_online() -> bool:
    with _lock:
        return (
            _status.tunnel == "ok"
            and bool(_status.mini_url)
            and _status.tunnel_reachable
        )
