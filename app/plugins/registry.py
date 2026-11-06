"""Lightweight plugin registry (extension surface)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PluginInfo:
    id: str
    name: str
    version: str
    description: str = ""


class PluginRegistry:
    """Register optional feature plugins without hard-wiring core."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._hooks: dict[str, list[Callable[..., None]]] = {}

    def register(self, info: PluginInfo) -> None:
        self._plugins[info.id] = info

    def list_plugins(self) -> list[PluginInfo]:
        return sorted(self._plugins.values(), key=lambda p: p.id)

    def add_hook(self, event: str, callback: Callable[..., None]) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event: str, **kwargs: object) -> None:
        for cb in self._hooks.get(event, []):
            cb(**kwargs)


# Process-wide registry (desktop + API share)
plugin_registry = PluginRegistry()

# Built-in placeholder plugins (documentation / discovery)
plugin_registry.register(
    PluginInfo(
        id="core.sync",
        name="Cloud Sync",
        version="1.0.0",
        description="Offline-first sync pull/push",
    )
)
plugin_registry.register(
    PluginInfo(
        id="core.telegram",
        name="Telegram",
        version="1.0.0",
        description="Customer + staff Telegram bots",
    )
)
