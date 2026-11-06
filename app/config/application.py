"""
Application bootstrap helpers for SMOXI Service.

This module coordinates high-level startup (settings, logging, paths)
without implementing business features or UI windows.
"""

from __future__ import annotations

from app.config.constants import APP_NAME, APP_SLUG, ORGANIZATION_NAME
from app.config.logging import configure_logging, get_logger
from app.config.settings import Settings, get_settings


class ApplicationContext:
    """
    Lightweight runtime context shared by desktop and server entry points.

    Designed to be Dependency-Injection friendly: construct once at process
    start and pass (or inject) into higher layers.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings: Settings = settings or get_settings()
        self.app_name: str = APP_NAME
        self.app_slug: str = APP_SLUG
        self.organization: str = ORGANIZATION_NAME

    def ensure_runtime_directories(self) -> None:
        """Create essential runtime directories if they do not exist."""
        for path in (
            self.settings.logs_dir,
            self.settings.uploads_dir,
            self.settings.backups_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def bootstrap(self) -> None:
        """
        Perform process-level bootstrap.

        Call this once from ``main.py`` / ``run.py`` before creating UI or API.
        """
        self.ensure_runtime_directories()
        configure_logging()
        from app.security.secret_bootstrap import ensure_runtime_secrets

        ensure_runtime_secrets()
        # Reload settings after possible secret minting.
        self.settings = get_settings()
        log = get_logger("application")
        log.info(
            "Bootstrapping {name} v{version} [{env}]",
            name=self.settings.app_name,
            version=self.settings.app_version,
            env=self.settings.environment,
        )


def create_application_context() -> ApplicationContext:
    """Factory for a fully prepared ApplicationContext."""
    context = ApplicationContext()
    context.bootstrap()
    return context
