"""Login screen."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import get_settings
from app.core.container import ServiceContainer
from app.core.enums import ThemeMode
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import get_translator, tr
from app.modules.auth.services.auth_service import AuthService
from app.ui.theme.theme_manager import ThemeManager


class LoginPage(QWidget):
    """Authentication page shown before the main shell."""

    login_succeeded = Signal(object)  # DesktopSession
    exit_requested = Signal()

    def __init__(self, container: ServiceContainer, theme_manager: ThemeManager) -> None:
        super().__init__()
        self._container = container
        self._theme_manager = theme_manager
        self._settings = get_settings()
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QWidget(objectName="LoginCard")
        card.setFixedWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        title = QLabel(tr("login.title"), objectName="PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self._company = QComboBox()
        self._username = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        self._remember = QCheckBox(tr("login.remember"))
        self._language = QComboBox()
        self._language.addItem("Oʻzbekcha", "uz_UZ")
        self._theme = QComboBox()
        self._theme.addItem(tr("theme.light"), ThemeMode.LIGHT.value)
        self._theme.addItem(tr("theme.dark"), ThemeMode.DARK.value)
        self._theme.addItem(tr("theme.system"), ThemeMode.SYSTEM.value)

        form.addRow(tr("login.company"), self._company)
        form.addRow(tr("login.username"), self._username)
        form.addRow(tr("login.password"), self._password)
        form.addRow("", self._remember)
        form.addRow(tr("login.language"), self._language)
        form.addRow(tr("login.theme"), self._theme)
        card_layout.addLayout(form)

        version_label = QLabel(
            tr("app.version", version=self._settings.app_version),
        )
        version_label.setStyleSheet("color: #5A6B7D; background: transparent;")
        license_label = QLabel(tr("app.license.active"))
        license_label.setStyleSheet("color: #5A6B7D; background: transparent;")
        card_layout.addWidget(version_label)
        card_layout.addWidget(license_label)

        buttons = QHBoxLayout()
        self._login_btn = QPushButton(tr("login.submit"))
        self._login_btn.setObjectName("PrimaryButton")
        self._login_btn.clicked.connect(self._on_login)
        self._exit_btn = QPushButton(tr("login.exit"))
        self._exit_btn.setObjectName("DangerButton")
        self._exit_btn.clicked.connect(self._on_exit)
        buttons.addWidget(self._exit_btn)
        buttons.addWidget(self._login_btn)
        card_layout.addLayout(buttons)

        forgot = QLabel(f'<a href="#forgot">{tr("login.forgot")}</a>')
        forgot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        forgot.setOpenExternalLinks(False)
        forgot.linkActivated.connect(self._on_forgot)
        card_layout.addWidget(forgot)

        outer.addWidget(card)
        self._load_companies()
        self._password.returnPressed.connect(self._on_login)

    def _on_forgot(self, _href: str = "") -> None:
        QMessageBox.information(
            self,
            tr("login.forgot"),
            tr("login.forgot_help"),
        )

    def _load_companies(self) -> None:
        from app.modules.companies.repositories.company_repository import CompanyRepository

        session = self._container.create_session()
        try:
            companies = CompanyRepository(session).list_active()
            for company in companies:
                self._company.addItem(company.name, company.code)
        finally:
            session.close()

    def _on_login(self) -> None:
        company_code = self._company.currentData()
        username = self._username.text().strip()
        password = self._password.text()

        locale = self._language.currentData()
        get_translator().set_locale(locale)

        theme_value = self._theme.currentData()
        from PySide6.QtWidgets import QApplication

        qapp = QApplication.instance()
        if qapp is not None:
            self._theme_manager.apply(qapp, theme_value)

        if not company_code or not username or not password:
            QMessageBox.warning(self, tr("common.error"), tr("login.error"))
            return

        session = self._container.create_session()
        try:
            auth = AuthService(session)
            result = auth.login(
                company_code=company_code,
                username=username,
                password=password,
                remember_me=self._remember.isChecked(),
            )
            session.commit()
            desktop_session = DesktopSession(user=result.user, token=result.session_token)
            self._container.set_current_user(result.user.id)
            self.login_succeeded.emit(desktop_session)
        except AppError as exc:
            session.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        except Exception:
            session.rollback()
            QMessageBox.warning(self, tr("common.error"), tr("login.error"))
        finally:
            session.close()

    def _on_exit(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("login.exit"),
            tr("login.exit_confirm"),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.exit_requested.emit()
