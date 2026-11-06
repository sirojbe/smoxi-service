"""Auto tunnel / Mini App URL helpers."""

from __future__ import annotations

from app.telegram.miniapp.tunnel import _URL_RE


def test_trycloudflare_url_regex() -> None:
    line = "INF |  https://random-words-123.trycloudflare.com "
    match = _URL_RE.search(line)
    assert match is not None
    assert match.group(0) == "https://random-words-123.trycloudflare.com"
