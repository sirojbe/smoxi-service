"""Qt desktop application bootstrap."""

from __future__ import annotations

import sys
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStackedWidget

from app.config.application import create_application_context
from app.config.constants import QT_APPLICATION, QT_ORGANIZATION
from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.core.enums import ThemeMode
from app.core.session import DesktopSession
from app.localization.translator import get_translator
from app.modules.auth.views.change_password_dialog import ChangePasswordDialog
from app.modules.auth.views.login_page import LoginPage
from app.telegram.miniapp.bootstrap import (
    check_bot_token,
    ensure_tunnel_health,
    shutdown_miniapp_tunnel,
    start_miniapp_with_tunnel,
    stop_tunnels,
)
from app.telegram.miniapp.server import MiniAppServer
from app.telegram.miniapp.tunnel import CloudflareTunnel
from app.telegram.poller import TelegramPoller, start_telegram_poller
from app.telegram.runtime_status import set_tunnel_status
from app.ui.shell.main_window import MainWindow
from app.ui.theme.theme_manager import ThemeManager

logger = get_logger("desktop")


class DesktopApplication:
    """Manage Qt application lifecycle."""

    def __init__(self) -> None:
        create_application_context()
        self._container = ServiceContainer.create()
        self._theme_manager = ThemeManager()
        self._session: DesktopSession | None = None
        self._pollers: list[TelegramPoller] = []
        self._miniapp_servers: list[MiniAppServer] = []
        self._tunnels: list[CloudflareTunnel] = []
        self._tunnel_health_timer: QTimer | None = None

    def run(self) -> int:
        """Start the desktop event loop."""
        app = QApplication(sys.argv)
        app.setOrganizationName(QT_ORGANIZATION)
        app.setApplicationName(QT_APPLICATION)
        app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
        )
        font = QFont("IBM Plex Sans", 10)
        app.setFont(font)
        self._theme_manager.apply(app, ThemeMode.LIGHT)

        stack = QStackedWidget()
        login = LoginPage(self._container, self._theme_manager)
        stack.addWidget(login)

        def on_login_success(desktop_session: DesktopSession) -> None:
            self._session = desktop_session
            get_translator().set_locale(desktop_session.user.locale)
            if desktop_session.user.must_change_password:
                dialog = ChangePasswordDialog(
                    self._container,
                    desktop_session,
                    forced=True,
                )
                if dialog.exec() != ChangePasswordDialog.DialogCode.Accepted:
                    self._session = None
                    self._container.set_current_user(None)
                    return
            main_window = MainWindow(
                self._container,
                desktop_session,
                self._theme_manager,
            )
            stack.addWidget(main_window)
            stack.setCurrentWidget(main_window)
            main_window.show()
            login.hide()
            company_id = desktop_session.user.company_id
            check_bot_token(self._container, company_id)
            try:
                start_miniapp_with_tunnel(
                    self._container,
                    company_id,
                    server_holder=self._miniapp_servers,
                    tunnel_holder=self._tunnels,
                )
            except Exception as exc:  # noqa: BLE001
                set_tunnel_status("fail", detail=str(exc))
                logger.warning("Mini App / tunnel ishga tushmadi: {}", exc)
            if self._tunnel_health_timer is None:
                self._tunnel_health_timer = QTimer()
                self._tunnel_health_timer.setInterval(45000)
                self._tunnel_health_timer.timeout.connect(
                    lambda: threading.Thread(
                        target=ensure_tunnel_health,
                        name="tunnel-health",
                        daemon=True,
                    ).start()
                )
            self._tunnel_health_timer.start()

            def _initial_tunnel_health() -> None:
                time.sleep(45.0)
                ensure_tunnel_health()

            threading.Thread(
                target=_initial_tunnel_health,
                name="tunnel-health-initial",
                daemon=True,
            ).start()
            try:
                start_telegram_poller(
                    self._container,
                    company_id,
                    holder=self._pollers,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Telegram poller ishga tushmadi: {}", exc)

        def on_exit() -> None:
            for poller in self._pollers:
                poller.stop()
            if self._session is not None:
                shutdown_miniapp_tunnel(self._container, self._session.user.company_id)
            else:
                stop_tunnels(self._tunnels)
            for server in self._miniapp_servers:
                server.stop()
            app.quit()

        login.login_succeeded.connect(on_login_success)
        login.exit_requested.connect(on_exit)
        stack.setMinimumSize(520, 640)
        stack.show()

        exit_code = app.exec()
        for poller in self._pollers:
            poller.stop()
        if self._session is not None:
            shutdown_miniapp_tunnel(self._container, self._session.user.company_id)
        else:
            stop_tunnels(self._tunnels)
        for server in self._miniapp_servers:
            server.stop()
        self._container.shutdown()
        return exit_code
