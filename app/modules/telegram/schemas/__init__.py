"""Telegram chat schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TelegramReplySchema(BaseModel):
    """Staff reply payload."""

    chat_id: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1, max_length=4000)
