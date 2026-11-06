"""Smoke test for Help page topics."""

from __future__ import annotations

from app.modules.help.views.help_page import _TOPICS


def test_help_topics_non_empty() -> None:
    assert len(_TOPICS) >= 5
    keys = {t[0] for t in _TOPICS}
    assert "help.topic_shortcuts" in keys
