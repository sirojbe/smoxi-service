"""Localization helpers."""

from __future__ import annotations

import json

from app.config.constants import DEFAULT_LOCALE
from app.config.settings import PROJECT_ROOT

_TRANSLATIONS_DIR = PROJECT_ROOT / "assets" / "translations"


class Translator:
    """Load and resolve UI strings for the active locale."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self._locale = locale
        self._catalog = self._load_catalog(locale)

    @property
    def locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        """Switch active locale and reload catalog."""
        self._locale = locale
        self._catalog = self._load_catalog(locale)

    def tr(self, key: str, **kwargs: object) -> str:
        """Return translated string for *key* with optional format kwargs."""
        template = self._catalog.get(key, key)
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, ValueError):
                return template
        return template

    def _load_catalog(self, locale: str) -> dict[str, str]:
        path = _TRANSLATIONS_DIR / f"{locale}.json"
        if not path.exists():
            path = _TRANSLATIONS_DIR / f"{DEFAULT_LOCALE}.json"
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)


_translator = Translator()


def get_translator() -> Translator:
    """Return the process-wide translator instance."""
    return _translator


def tr(key: str, **kwargs: object) -> str:
    """Shortcut for ``get_translator().tr``."""
    return _translator.tr(key, **kwargs)
