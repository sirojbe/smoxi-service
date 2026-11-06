"""Force password change dialog (first login / weak default)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.auth.services.auth_service import AuthService


class ChangePasswordDialog(QDialog):
    """Require a stronger password before entering the shell."""

    def __init__(
        self,
        container: ServiceContainer,
        session: DesktopSession,
        parent=None,
        *,
        forced: bool = False,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._session = session
        self.setWindowTitle(tr("auth.change_password_title"))
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        hint = QLabel(
            tr("auth.change_password_forced")
            if forced
            else tr("auth.change_password_hint")
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        self._current = QLineEdit()
        self._current.setEchoMode(QLineEdit.EchoMode.Password)
        self._new = QLineEdit()
        self._new.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("auth.current_password"), self._current)
        form.addRow(tr("auth.new_password"), self._new)
        form.addRow(tr("auth.confirm_password"), self._confirm)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText(tr("common.save"))
            ok_btn.setObjectName("PrimaryButton")
        if not forced:
            buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
            cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if cancel_btn is not None:
                cancel_btn.setText(tr("common.cancel"))
            buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._submit)
        layout.addWidget(buttons)
        self._new.setPlaceholderText(tr("auth.new_password_hint"))

    def _submit(self) -> None:
        new = self._new.text().strip()
        confirm = self._confirm.text().strip()
        if new != confirm:
            QMessageBox.warning(self, tr("common.error"), tr("auth.password_mismatch"))
            return
        db = self._container.create_session()
        try:
            AuthService(db).change_password(
                self._session.user.id,
                current_password=self._current.text(),
                new_password=new,
            )
            db.commit()
            self._session.user.must_change_password = False
            self.accept()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        except Exception:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), tr("common.unexpected_error"))
        finally:
            db.close()
