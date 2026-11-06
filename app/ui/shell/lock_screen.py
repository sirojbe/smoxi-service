"""Workstation lock overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.auth.services.auth_service import AuthService


class LockScreenDialog(QDialog):
    """Modal lock until current user re-enters password."""

    logout_requested = Signal()

    def __init__(
        self,
        parent: QWidget,
        container: ServiceContainer,
        session: DesktopSession,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._session = session
        self.setWindowTitle(tr("lock.title"))
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(tr("lock.title"), objectName="PageTitle"))
        root.addWidget(
            QLabel(tr("lock.subtitle", name=session.display_name))
        )
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText(tr("login.password"))
        self._password.returnPressed.connect(self._unlock)
        root.addWidget(self._password)
        row = QHBoxLayout()
        logout_btn = QPushButton(tr("lock.logout"))
        logout_btn.setObjectName("DangerButton")
        logout_btn.clicked.connect(self._logout)
        unlock_btn = QPushButton(tr("lock.unlock"))
        unlock_btn.setObjectName("PrimaryButton")
        unlock_btn.clicked.connect(self._unlock)
        row.addWidget(logout_btn)
        row.addStretch()
        row.addWidget(unlock_btn)
        root.addLayout(row)
        self._password.setFocus()

    def reject(self) -> None:
        """Block Esc / close without unlock."""
        return

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    def _unlock(self) -> None:
        password = self._password.text()
        if not password:
            QMessageBox.warning(self, tr("common.error"), tr("lock.password_required"))
            return
        db = self._container.create_session()
        try:
            AuthService(db).verify_user_password(self._session.user_id, password)
            db.commit()
        except AppError as exc:
            db.rollback()
            self._password.clear()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.done(QDialog.DialogCode.Accepted)

    def _logout(self) -> None:
        self.logout_requested.emit()
        self.done(QDialog.DialogCode.Rejected)
