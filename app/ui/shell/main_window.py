"""Main application window shell."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import get_settings
from app.core.container import ServiceContainer
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.administration.views.administration_page import AdministrationPage
from app.modules.ai_assistant.views.ai_assistant_page import AiAssistantPage
from app.modules.auth.services.auth_service import AuthService
from app.modules.automation.views.automation_page import AutomationPage
from app.modules.business_clients.views.companies_page import CompaniesPage
from app.modules.calendar.views.calendar_page import CalendarPage
from app.modules.customers.views.customers_page import CustomersPage
from app.modules.dashboard.views.dashboard_page import DashboardPage
from app.modules.finance.views.finance_page import FinancePage
from app.modules.help.views.about_page import AboutPage
from app.modules.help.views.help_page import HelpPage
from app.modules.inventory.views.inventory_page import InventoryPage
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.notifications.views.notifications_page import NotificationsPage
from app.modules.payments.views.payments_page import PaymentsPage
from app.modules.reception.views.reception_page import ReceptionPage
from app.modules.reports.views.reports_page import ReportsPage
from app.modules.settings.views.settings_page import SettingsPage
from app.modules.suppliers.views.suppliers_page import SuppliersPage
from app.modules.sync.views.sync_page import SyncPage
from app.modules.technicians.views.technicians_page import TechniciansPage
from app.modules.telegram.repositories.message_repository import TelegramMessageRepository
from app.modules.telegram.views.telegram_page import TelegramPage
from app.modules.warehouse.views.warehouse_page import WarehousePage
from app.modules.work_orders.views.work_orders_page import WorkOrdersPage
from app.security.route_permissions import allowed_routes
from app.telegram.miniapp.bootstrap import check_bot_token
from app.telegram.runtime_status import get_telegram_runtime_status
from app.ui.shell.global_search import install_global_search_shortcut
from app.ui.shell.idle_lock import IdleLockWatcher
from app.ui.shell.lock_screen import LockScreenDialog
from app.ui.shell.shell_prefs import load_shell_prefs
from app.ui.shell.sidebar import Sidebar
from app.ui.theme.theme_manager import ThemeManager


class MainWindow(QMainWindow):
    """Enterprise shell with sidebar, workspace, and status bar."""

    def __init__(
        self,
        container: ServiceContainer,
        session: DesktopSession,
        theme_manager: ThemeManager,
    ) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._theme_manager = theme_manager
        self._settings = get_settings()
        self._pages: dict[str, QWidget] = {}
        self._last_notif_unread = 0
        self._locked = False
        self._build_ui()
        self._apply_rbac()
        self._wire_navigation()
        install_global_search_shortcut(
            self, self._container, self._session, self._open_search_target
        )
        self._idle = IdleLockWatcher(self)
        self._idle.idle_timeout.connect(self._lock_screen)
        prefs = load_shell_prefs()
        self._idle.set_idle_minutes(prefs.idle_lock_minutes)
        self._badge_timer = QTimer(self)
        self._badge_timer.setInterval(3000)
        self._badge_timer.timeout.connect(self._refresh_badges)
        self._badge_timer.start()
        self._refresh_badges()
        self._bot_timer = QTimer(self)
        self._bot_timer.setInterval(8000)
        self._bot_timer.timeout.connect(self._refresh_bot_status)
        self._bot_timer.start()
        self._refresh_bot_status()

    def _build_ui(self) -> None:
        self.setWindowTitle(tr("app.name"))
        self.resize(1440, 900)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.route_selected.connect(self._on_route)
        root.addWidget(self._sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        top_bar = QWidget(objectName="TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)
        brand = QLabel(tr("app.name"))
        brand.setObjectName("BrandLabel")
        self._search_btn = QPushButton(tr("common.search") + "  ·  Ctrl+K")
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.setFlat(True)
        self._search_btn.clicked.connect(self._open_global_search)
        self._branch_box = QComboBox()
        self._branch_box.setMinimumWidth(160)
        self._branch_box.currentIndexChanged.connect(self._on_branch_changed)
        self._theme_btn = QPushButton(tr("theme.toggle"))
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)
        self._lock_btn = QPushButton(tr("lock.button"))
        self._lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lock_btn.clicked.connect(self._lock_screen)
        self._bell = QPushButton(tr("notifications.bell"))
        self._bell.setObjectName("PrimaryButton")
        self._bell.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bell.clicked.connect(lambda: self._on_route("notifications"))
        top_layout.addWidget(brand)
        top_layout.addStretch()
        top_layout.addWidget(self._search_btn)
        top_layout.addWidget(self._branch_box)
        top_layout.addWidget(self._theme_btn)
        top_layout.addWidget(self._lock_btn)
        top_layout.addWidget(self._bell)
        right.addWidget(top_bar)

        self._stack = QStackedWidget(objectName="Workspace")
        right.addWidget(self._stack, stretch=1)

        from app.ui.widgets.toast_banner import ToastBanner

        self._toast = ToastBanner(self._stack)

        status = QWidget(objectName="StatusBar")
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(12, 4, 12, 4)
        self._status_bot = QLabel(tr("status.bot_checking"))
        self._status_sync = QLabel(tr("status.synced"))
        self._status_branch = QLabel(tr("status.branch", name="—"))
        self._status_user = QLabel(tr("status.user", name=self._session.display_name))
        self._status_version = QLabel(tr("app.version", version=self._settings.app_version))
        status_layout.addWidget(self._status_bot)
        status_layout.addWidget(self._status_sync)
        status_layout.addWidget(self._status_branch)
        status_layout.addStretch()
        status_layout.addWidget(self._status_user)
        status_layout.addWidget(self._status_version)
        right.addWidget(status)

        root.addLayout(right, stretch=1)
        self.setCentralWidget(central)
        self._load_branches()

    def _apply_rbac(self) -> None:
        codes: set[str] = set()
        role = self._session.user.role
        if role is not None:
            codes = {p.code for p in role.permissions}
        self._allowed_routes = allowed_routes(codes)
        self._sidebar.apply_allowed_routes(self._allowed_routes)

    def _wire_navigation(self) -> None:
        for route_id, _label_key in Sidebar.ROUTES:
            if route_id == "logout":
                continue
            if route_id not in self._allowed_routes:
                continue
            if route_id == "dashboard":
                page = DashboardPage(self._container, self._session)
                page.navigate_requested.connect(self._on_route)
            elif route_id == "customers":
                page = CustomersPage(self._container, self._session)
            elif route_id == "companies":
                page = CompaniesPage(self._container, self._session)
            elif route_id == "reception":
                page = ReceptionPage(self._container, self._session)
            elif route_id == "work_orders":
                page = WorkOrdersPage(self._container, self._session)
            elif route_id == "technicians":
                page = TechniciansPage(self._container, self._session)
            elif route_id == "inventory":
                page = InventoryPage(self._container, self._session)
            elif route_id == "warehouse":
                page = WarehousePage(self._container, self._session)
            elif route_id == "suppliers":
                page = SuppliersPage(self._container, self._session)
            elif route_id == "finance":
                page = FinancePage(self._container, self._session)
            elif route_id == "payments":
                page = PaymentsPage(self._container, self._session)
            elif route_id == "reports":
                page = ReportsPage(self._container, self._session)
            elif route_id == "calendar":
                page = CalendarPage(self._container, self._session)
            elif route_id == "notifications":
                page = NotificationsPage(self._container, self._session)
                page.open_route_requested.connect(self._open_notification_target)
            elif route_id == "telegram":
                page = TelegramPage(self._container, self._session)
            elif route_id == "automation":
                page = AutomationPage(self._container, self._session)
            elif route_id == "ai_assistant":
                page = AiAssistantPage(self._container, self._session)
                page.navigate_requested.connect(self._on_route)
            elif route_id == "settings":
                page = SettingsPage(self._container, self._session)
            elif route_id == "administration":
                page = AdministrationPage(self._container, self._session)
            elif route_id == "sync":
                page = SyncPage(self._container, self._session)
            elif route_id == "help":
                page = HelpPage()
            elif route_id == "about":
                page = AboutPage()
            else:
                continue
            self._pages[route_id] = page
            self._stack.addWidget(page)
        if not self._pages:
            return
        start = "dashboard" if "dashboard" in self._pages else next(iter(self._pages))
        self._stack.setCurrentWidget(self._pages[start])
        self._sidebar.select_route(start)

    def _load_branches(self) -> None:
        from app.modules.branches.services.branch_service import BranchService

        db = self._container.create_session()
        try:
            branches = BranchService(db).list_branches(self._session.user.company_id)
            db.commit()
        finally:
            db.close()
        self._branch_box.blockSignals(True)
        self._branch_box.clear()
        selected = self._session.active_branch_id
        for branch in branches:
            self._branch_box.addItem(branch.name, branch.id)
            if selected is None and branch.is_default:
                selected = branch.id
        if selected is not None:
            idx = self._branch_box.findData(selected)
            if idx >= 0:
                self._branch_box.setCurrentIndex(idx)
                self._session.active_branch_id = int(selected)
        self._branch_box.blockSignals(False)
        self._update_branch_status()

    def _on_branch_changed(self, _index: int) -> None:
        branch_id = self._branch_box.currentData()
        if branch_id is None:
            return
        self._session.active_branch_id = int(branch_id)
        self._update_branch_status()
        page = self._pages.get("work_orders")
        if page is not None and hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception:  # noqa: BLE001
                pass

    def _update_branch_status(self) -> None:
        name = self._branch_box.currentText() or "—"
        self._status_branch.setText(tr("status.branch", name=name))

    def _lock_screen(self) -> None:
        if self._locked:
            return
        self._locked = True
        self._idle.pause()
        dialog = LockScreenDialog(self, self._container, self._session)
        dialog.logout_requested.connect(self._logout_from_lock)
        result = dialog.exec()
        self._locked = False
        if result == LockScreenDialog.DialogCode.Accepted:
            prefs = load_shell_prefs()
            self._idle.set_idle_minutes(prefs.idle_lock_minutes)
        # Rejected = logout already handled

    def _logout_from_lock(self) -> None:
        self._badge_timer.stop()
        self._bot_timer.stop()
        db_session = self._container.create_session()
        try:
            AuthService(db_session).logout(
                self._session.token, actor_id=self._session.user_id
            )
            db_session.commit()
        finally:
            db_session.close()
        self._container.set_current_user(None)
        self.close()

    def _open_global_search(self) -> None:
        from app.ui.shell.global_search import GlobalSearchDialog

        dialog = GlobalSearchDialog(self, self._container, self._session)
        dialog.navigate_requested.connect(self._open_search_target)
        dialog.exec()

    def _open_search_target(self, route: str, ref: object) -> None:
        self._on_route(route)
        if not ref:
            return
        page = self._pages.get(route)
        if page is not None and hasattr(page, "focus_entity"):
            try:
                page.focus_entity(ref)
            except Exception:  # noqa: BLE001
                pass

    def _toggle_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        self._theme_manager.toggle(app)

    def _refresh_bot_status(self) -> None:
        check_bot_token(self._container, self._session.user.company_id)
        st = get_telegram_runtime_status()
        if st.bot == "ok":
            name = f"@{st.bot_detail}" if st.bot_detail else ""
            text = tr("status.bot_ok", name=name).strip()
        elif st.bot == "no_token":
            text = tr("status.bot_no_token")
        elif st.bot == "fail":
            text = tr("status.bot_fail")
        else:
            text = tr("status.bot_checking")
        if st.tunnel == "ok" and st.tunnel_reachable and st.mini_url:
            text = f"{text}  ·  Mini App ✓"
        elif st.tunnel in {"starting", "idle"} or (
            st.tunnel == "ok" and st.mini_url and not st.tunnel_reachable
        ):
            text = f"{text}  ·  Mini App…"
        elif st.tunnel == "fail":
            detail = f": {st.tunnel_detail}" if st.tunnel_detail else ""
            text = f"{text}  ·  Mini App ✗{detail}"
        self._status_bot.setText(text)

    def _refresh_badges(self) -> None:
        company_id = self._session.user.company_id
        db = self._container.create_session()
        try:
            notif_svc = NotificationService(db)
            notif_unread = notif_svc.count_unread(company_id)
            latest = notif_svc.list_notifications(company_id, unread_only=True)[:1]
            tg_unread = TelegramMessageRepository(db).count_unread(company_id)
            from app.modules.sync.services.sync_service import SyncService

            pending_sync = SyncService(db).count_pending(company_id)
        finally:
            db.close()
        self._sidebar.set_badge("notifications", notif_unread)
        self._sidebar.set_badge("telegram", tg_unread)
        if notif_unread > 0:
            self._bell.setText(tr("notifications.bell_count", count=notif_unread))
        else:
            self._bell.setText(tr("notifications.bell"))
        if pending_sync > 0:
            self._status_sync.setText(tr("status.sync_pending", count=pending_sync))
        else:
            self._status_sync.setText(tr("status.synced"))

        if notif_unread > self._last_notif_unread and latest:
            self._maybe_toast(latest[0].title, latest[0].kind)
        self._last_notif_unread = notif_unread

    def show_toast(self, text: str, *, ms: int = 3500) -> None:
        """Show a non-blocking toast message in the workspace."""
        self._toast.show_message(text, ms=ms)

    def _maybe_toast(self, title: str, kind: str) -> None:
        from app.modules.notifications.services.prefs import (
            channel_allowed,
            is_quiet_hours,
            load_notification_prefs,
        )

        prefs = load_notification_prefs()
        if not prefs.toast_enabled:
            return
        if is_quiet_hours(prefs):
            return
        if not channel_allowed(prefs, kind):
            return
        self.show_toast(title)

    def _open_notification_target(self, route: str, ref_key: object) -> None:
        self._on_route(route)
        if route == "telegram" and ref_key:
            page = self._pages.get("telegram")
            if isinstance(page, TelegramPage):
                page.open_chat(str(ref_key))
        self._refresh_badges()

    def _on_route(self, route_id: str) -> None:
        if route_id == "logout":
            self._logout()
            return
        if route_id not in self._allowed_routes:
            QMessageBox.warning(self, tr("common.error"), tr("auth.no_permission"))
            return
        page = self._pages.get(route_id)
        if page is not None:
            self._stack.setCurrentWidget(page)
            self._sidebar.select_route(route_id)
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:  # noqa: BLE001
                    pass
            self._refresh_badges()

    def _logout(self) -> None:
        answer = QMessageBox.question(self, tr("nav.logout"), tr("logout.confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._idle.pause()
        self._badge_timer.stop()
        self._bot_timer.stop()
        db_session = self._container.create_session()
        try:
            AuthService(db_session).logout(self._session.token, actor_id=self._session.user_id)
            db_session.commit()
        finally:
            db_session.close()
        self._container.set_current_user(None)
        self.close()
