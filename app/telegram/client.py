"""Telegram Bot API HTTP client (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.config.logging import get_logger

logger = get_logger("telegram")


class TelegramClientError(Exception):
    """Telegram API request failed."""


class TelegramClient:
    """Minimal Telegram Bot API wrapper."""

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token.strip()
        if not self._token:
            raise TelegramClientError("Telegram bot token boʻsh.")

    def _request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("Telegram HTTP xato: {} {}", exc.code, detail)
            raise TelegramClientError(f"Telegram xatosi ({exc.code}).") from exc
        except urllib.error.URLError as exc:
            logger.error("Telegram tarmoq xatosi: {}", exc)
            raise TelegramClientError("Telegramga ulanib boʻlmadi (internet).") from exc
        if not body.get("ok"):
            raise TelegramClientError(str(body.get("description", "Telegram xatosi")))
        return body

    def get_me(self) -> dict[str, Any]:
        return self._request("getMe", {})

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._request("sendMessage", payload)

    def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        self._request(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text},
        )

    def get_updates(self, *, offset: int | None = None, timeout: int = 25) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        result = self._request("getUpdates", payload)
        updates = result.get("result", [])
        return updates if isinstance(updates, list) else []

    def set_chat_menu_button(
        self,
        *,
        chat_id: str | int | None = None,
        text: str = "SMOXI",
        web_app_url: str,
    ) -> dict[str, Any]:
        """Attach a Mini App menu button (optionally for one chat)."""
        payload: dict[str, Any] = {
            "menu_button": {
                "type": "web_app",
                "text": text[:16] or "SMOXI",
                "web_app": {"url": web_app_url},
            }
        }
        if chat_id is not None:
            payload["chat_id"] = chat_id
        return self._request("setChatMenuButton", payload)

    def clear_chat_menu_button(self, *, chat_id: str | int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"menu_button": {"type": "commands"}}
        if chat_id is not None:
            payload["chat_id"] = chat_id
        return self._request("setChatMenuButton", payload)
