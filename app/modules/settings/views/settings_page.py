"""Settings page — company, users, backup/restore."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.notifications.services.prefs import (
    NotificationPrefs,
    load_notification_prefs,
    save_notification_prefs,
)
from app.modules.settings.services.settings_service import CompanyUpdateSchema, SettingsService
from app.ui.widgets.toast import show_toast


class SettingsPage(QWidget):
    """Application and company settings."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)
        outer.addWidget(QLabel(tr("settings.title"), objectName="PageTitle"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, stretch=1)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        scroll.setWidget(content)

        company_card, company_body = self._make_section(tr("settings.company_section"))
        form = QFormLayout()
        form.setSpacing(10)
        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._tax = QLineEdit()
        self._address = QLineEdit()
        form.addRow(tr("settings.company_name"), self._name)
        form.addRow(tr("settings.phone"), self._phone)
        form.addRow(tr("settings.email"), self._email)
        form.addRow(tr("settings.tax_id"), self._tax)
        form.addRow(tr("settings.address"), self._address)
        self._tg_token = QLineEdit()
        self._tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._tg_username = QLineEdit()
        self._tg_username.setPlaceholderText("@smoxi_bot")
        form.addRow(tr("settings.telegram_token"), self._tg_token)
        form.addRow(tr("settings.telegram_username"), self._tg_username)
        self._staff_ids = QLineEdit()
        self._staff_ids.setPlaceholderText("12646845,64665666")
        form.addRow(tr("settings.staff_chat_ids"), self._staff_ids)
        self._mini_url = QLineEdit()
        self._mini_url.setPlaceholderText(tr("settings.mini_app_auto"))
        mini_row = QWidget()
        mini_layout = QVBoxLayout(mini_row)
        mini_layout.setContentsMargins(0, 0, 0, 0)
        mini_layout.setSpacing(4)
        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(8)
        self._mini_status_dot = QLabel()
        self._mini_status_dot.setObjectName("StatusDot")
        self._mini_status_dot.setFixedSize(12, 12)
        self._mini_status_dot.setProperty("state", "pending")
        url_row.addWidget(self._mini_status_dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        url_row.addWidget(self._mini_url, stretch=1)
        mini_layout.addLayout(url_row)
        self._mini_status_label = QLabel(tr("settings.mini_app_starting"))
        self._mini_status_label.setObjectName("HintLabel")
        mini_layout.addWidget(self._mini_status_label)
        form.addRow(tr("settings.mini_app_url"), mini_row)
        self._cf_token = QLineEdit()
        self._cf_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._cf_token.setPlaceholderText(tr("settings.cf_tunnel_token_ph"))
        form.addRow(tr("settings.cf_tunnel_token"), self._cf_token)
        company_body.addLayout(form)
        self._staff_hint = QLabel(tr("settings.staff_bot_hint"))
        self._staff_hint.setWordWrap(True)
        self._staff_hint.setObjectName("HintLabel")
        company_body.addWidget(self._staff_hint)
        self._tunnel_hint = QLabel(tr("settings.named_tunnel_hint"))
        self._tunnel_hint.setWordWrap(True)
        self._tunnel_hint.setObjectName("HintLabel")
        company_body.addWidget(self._tunnel_hint)
        save_btn = QPushButton(tr("common.save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save_company)
        company_body.addWidget(save_btn)
        root.addWidget(company_card)

        notif_card, notif_body = self._make_section(tr("settings.notifications_section"))
        notif_form = QFormLayout()
        notif_form.setSpacing(10)
        self._toast_enabled = QCheckBox(tr("settings.notif_toast"))
        self._quiet_enabled = QCheckBox(tr("settings.notif_quiet"))
        self._quiet_start = QSpinBox()
        self._quiet_start.setRange(0, 23)
        self._quiet_end = QSpinBox()
        self._quiet_end.setRange(0, 23)
        self._ch_telegram = QCheckBox(tr("settings.notif_ch_telegram"))
        self._ch_wo = QCheckBox(tr("settings.notif_ch_work_order"))
        self._ch_system = QCheckBox(tr("settings.notif_ch_system"))
        notif_form.addRow(self._toast_enabled)
        notif_form.addRow(self._quiet_enabled)
        notif_form.addRow(tr("settings.notif_quiet_start"), self._quiet_start)
        notif_form.addRow(tr("settings.notif_quiet_end"), self._quiet_end)
        notif_form.addRow(self._ch_telegram)
        notif_form.addRow(self._ch_wo)
        notif_form.addRow(self._ch_system)
        notif_body.addLayout(notif_form)
        notif_save = QPushButton(tr("settings.notif_save"))
        notif_save.clicked.connect(self._save_notif_prefs)
        notif_body.addWidget(notif_save)
        root.addWidget(notif_card)

        users_card, users_body = self._make_section(tr("settings.users_section"))
        users_toolbar = QHBoxLayout()
        add_user_btn = QPushButton(tr("settings.user_add"))
        add_user_btn.setObjectName("PrimaryButton")
        add_user_btn.clicked.connect(self._add_user)
        role_btn = QPushButton(tr("settings.user_change_role"))
        role_btn.clicked.connect(self._change_role)
        toggle_btn = QPushButton(tr("settings.user_toggle_active"))
        toggle_btn.clicked.connect(self._toggle_user)
        roles_btn = QPushButton(tr("settings.roles_matrix"))
        roles_btn.clicked.connect(self._show_roles)
        users_toolbar.addWidget(add_user_btn)
        users_toolbar.addWidget(role_btn)
        users_toolbar.addWidget(toggle_btn)
        users_toolbar.addWidget(roles_btn)
        users_toolbar.addStretch()
        users_body.addLayout(users_toolbar)
        self._users_table = QTableWidget(0, 4)
        self._users_table.setHorizontalHeaderLabels(
            [
                tr("settings.username"),
                tr("settings.full_name"),
                tr("settings.role"),
                tr("settings.user_status"),
            ]
        )
        self._users_table.horizontalHeader().setStretchLastSection(True)
        self._users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._users_table.setMinimumHeight(180)
        self._users_table.setMaximumHeight(240)
        users_body.addWidget(self._users_table)
        root.addWidget(users_card)

        branch_card, branch_body = self._make_section(tr("branches.section"))
        branch_row = QHBoxLayout()
        self._branches_info = QLabel()
        self._branches_info.setWordWrap(True)
        add_branch_btn = QPushButton(tr("branches.add"))
        add_branch_btn.clicked.connect(self._add_branch)
        branch_row.addWidget(self._branches_info, stretch=1)
        branch_row.addWidget(add_branch_btn)
        branch_body.addLayout(branch_row)
        root.addWidget(branch_card)

        shell_card, shell_body = self._make_section(tr("settings.shell_section"))
        shell_form = QFormLayout()
        self._idle_minutes = QSpinBox()
        self._idle_minutes.setRange(0, 120)
        self._idle_minutes.setSpecialValueText(tr("settings.idle_off"))
        shell_form.addRow(tr("settings.idle_lock_minutes"), self._idle_minutes)
        shell_body.addLayout(shell_form)
        idle_save = QPushButton(tr("settings.idle_save"))
        idle_save.clicked.connect(self._save_shell_prefs)
        shell_body.addWidget(idle_save)
        root.addWidget(shell_card)

        license_card, license_body = self._make_section(tr("settings.license_section"))
        license_row = QHBoxLayout()
        self._license_info = QLabel()
        self._license_info.setWordWrap(True)
        activate_btn = QPushButton(tr("settings.license_activate"))
        activate_btn.clicked.connect(self._activate_license)
        license_row.addWidget(self._license_info, stretch=1)
        license_row.addWidget(activate_btn)
        license_body.addLayout(license_row)
        root.addWidget(license_card)

        backup_card, backup_body = self._make_section(tr("settings.backup_section"))
        backup_row = QHBoxLayout()
        backup_btn = QPushButton(tr("settings.backup_now"))
        backup_btn.clicked.connect(self._backup)
        restore_btn = QPushButton(tr("settings.restore_latest"))
        restore_btn.clicked.connect(self._restore)
        self._backup_info = QLabel()
        self._backup_info.setWordWrap(True)
        backup_row.addWidget(backup_btn)
        backup_row.addWidget(restore_btn)
        backup_row.addWidget(self._backup_info, stretch=1)
        backup_body.addLayout(backup_row)
        root.addWidget(backup_card)
        root.addStretch()
        self._mini_timer = QTimer(self)
        self._mini_timer.setInterval(3000)
        self._mini_timer.timeout.connect(self._refresh_mini_app_status)
        self._mini_timer.start()
        self.reload()

    def _make_section(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        """Build a scroll-friendly card section."""
        card = QFrame(objectName="IntakeCard")
        body = QVBoxLayout(card)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(10)
        header = QLabel(title)
        header.setObjectName("PageTitle")
        body.addWidget(header)
        return card, body

    def reload(self) -> None:
        db = self._container.create_session()
        try:
            service = SettingsService(db)
            company = service.get_company(self._session.user.company_id)
            self._name.setText(company.name)
            self._phone.setText(company.phone or "")
            self._email.setText(company.email or "")
            self._tax.setText(company.tax_id or "")
            self._address.setText(company.address or "")
            from app.security.secrets import company_bot_token

            self._tg_token.setText(company_bot_token(company))
            self._tg_username.setText(company.telegram_bot_username or "")
            self._staff_ids.setText(company.telegram_staff_chat_ids or "")
            self._mini_url.setText(company.telegram_mini_app_url or "")
            from app.security.secrets import decrypt_secret

            self._cf_token.setText(decrypt_secret(company.cloudflare_tunnel_token))
            db.commit()
            users = service.list_users(self._session.user.company_id)
            self._users_table.setRowCount(0)
            for row, user in enumerate(users):
                self._users_table.insertRow(row)
                role_name = user.role.name if user.role else ""
                status = tr("settings.user_active") if user.is_active else tr("settings.user_inactive")
                values = [user.username, user.full_name, role_name, status]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setData(Qt.ItemDataRole.UserRole, user.id)
                    self._users_table.setItem(row, col, item)
            from app.modules.branches.services.branch_service import BranchService

            branches = BranchService(db).list_branches(self._session.user.company_id)
            self._branches_info.setText(
                ", ".join(f"{b.code}:{b.name}" for b in branches) or "—"
            )
            from app.ui.shell.shell_prefs import load_shell_prefs

            self._idle_minutes.setValue(load_shell_prefs().idle_lock_minutes)
            from app.modules.license.services.license_service import LicenseService

            lic = LicenseService(db).get_status(self._session.user.company_id)
            expires = ""
            if lic.expires_at is not None:
                expires = lic.expires_at.strftime("%d.%m.%Y")
            self._license_info.setText(
                tr(
                    "settings.license_status",
                    plan=lic.plan_code,
                    status=lic.status,
                    seats=f"{lic.seats_used}/{lic.seats}",
                    expires=expires or "—",
                    license_key=lic.license_key_masked,
                )
            )
            backups = service.list_backups()
            if backups:
                self._backup_info.setText(tr("settings.last_backup", name=backups[0].name))
            else:
                self._backup_info.setText(tr("settings.no_backup"))
            prefs = load_notification_prefs()
            self._toast_enabled.setChecked(prefs.toast_enabled)
            self._quiet_enabled.setChecked(prefs.quiet_enabled)
            self._quiet_start.setValue(prefs.quiet_start_hour)
            self._quiet_end.setValue(prefs.quiet_end_hour)
            self._ch_telegram.setChecked(prefs.channel_telegram)
            self._ch_wo.setChecked(prefs.channel_work_order)
            self._ch_system.setChecked(prefs.channel_system)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()
        self._refresh_mini_app_status()

    def _refresh_mini_app_status(self) -> None:
        from app.telegram.runtime_status import get_telegram_runtime_status

        st = get_telegram_runtime_status()
        runtime_url = (st.mini_url or "").strip()
        if runtime_url:
            self._mini_url.setText(runtime_url)

        if st.tunnel == "ok" and st.tunnel_reachable and runtime_url:
            state = "ok"
            text = tr("settings.mini_app_ok")
            tip = runtime_url
        elif st.tunnel == "ok" and runtime_url and not st.tunnel_reachable:
            state = "pending"
            detail = (st.tunnel_detail or "").strip()
            text = detail or tr("settings.mini_app_checking")
            tip = detail or tr("settings.mini_app_checking")
        elif st.tunnel == "fail":
            state = "fail"
            detail = (st.tunnel_detail or "").strip()
            text = tr("settings.mini_app_fail")
            tip = f"{text}\n{detail}" if detail else text
        elif st.tunnel in {"starting", "idle"}:
            state = "pending"
            text = tr("settings.mini_app_starting")
            tip = text
        else:
            state = "pending"
            text = tr("settings.mini_app_waiting")
            tip = text

        self._mini_status_dot.setProperty("state", state)
        self._mini_status_dot.style().unpolish(self._mini_status_dot)
        self._mini_status_dot.style().polish(self._mini_status_dot)
        self._mini_status_label.setText(text)
        self._mini_status_dot.setToolTip(tip)
        self._mini_status_label.setToolTip(tip)

    def _save_notif_prefs(self) -> None:
        save_notification_prefs(
            NotificationPrefs(
                toast_enabled=self._toast_enabled.isChecked(),
                quiet_enabled=self._quiet_enabled.isChecked(),
                quiet_start_hour=self._quiet_start.value(),
                quiet_end_hour=self._quiet_end.value(),
                channel_telegram=self._ch_telegram.isChecked(),
                channel_work_order=self._ch_wo.isChecked(),
                channel_system=self._ch_system.isChecked(),
            )
        )
        QMessageBox.information(self, tr("settings.title"), tr("settings.notif_saved"))

    def _save_company(self) -> None:
        try:
            payload = CompanyUpdateSchema(
                name=self._name.text(),
                phone=self._phone.text(),
                email=self._email.text(),
                tax_id=self._tax.text(),
                address=self._address.text(),
                telegram_bot_token=self._tg_token.text(),
                telegram_bot_username=self._tg_username.text(),
                telegram_staff_chat_ids=self._staff_ids.text(),
                telegram_mini_app_url=self._mini_url.text(),
                cloudflare_tunnel_token=self._cf_token.text(),
            )
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
            return
        db = self._container.create_session()
        try:
            company = SettingsService(db).update_company(
                self._session.user.company_id,
                payload,
                actor_id=self._session.user_id,
            )
            db.commit()
            from app.security.secrets import company_bot_token

            token = company_bot_token(company)
            if token:
                try:
                    from app.telegram.client import TelegramClient
                    from app.telegram.staff_bot import sync_staff_menu_button

                    sync_staff_menu_button(TelegramClient(token), company)
                except Exception:
                    pass
            show_toast(self, tr("settings.saved"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _backup(self) -> None:
        db = self._container.create_session()
        try:
            path = SettingsService(db).create_backup(actor_id=self._session.user_id)
            db.commit()
            QMessageBox.information(
                self,
                tr("settings.title"),
                tr("settings.backup_ok", path=str(path)),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _restore(self) -> None:
        db = self._container.create_session()
        try:
            service = SettingsService(db)
            backups = service.list_backups()
            if not backups:
                QMessageBox.information(self, tr("settings.title"), tr("settings.no_backup"))
                return
            latest = backups[0]
            answer = QMessageBox.question(
                self,
                tr("settings.restore_latest"),
                tr("settings.restore_confirm", name=latest.name),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            service.restore_backup(Path(latest), actor_id=self._session.user_id)
            db.commit()
            QMessageBox.information(
                self,
                tr("settings.title"),
                tr("settings.restore_ok"),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _selected_user_id(self) -> int | None:
        rows = self._users_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._users_table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _add_user(self) -> None:
        db = self._container.create_session()
        try:
            roles = SettingsService(db).list_roles()
        finally:
            db.close()
        if not roles:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("settings.user_add"))
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        username = QLineEdit()
        full_name = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        role_box = QComboBox()
        for role in roles:
            role_box.addItem(role.name, role.id)
        form.addRow(tr("settings.username"), username)
        form.addRow(tr("settings.full_name"), full_name)
        form.addRow(tr("login.password"), password)
        form.addRow(tr("settings.role"), role_box)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            SettingsService(db).create_user(
                self._session.user.company_id,
                username=username.text(),
                password=password.text(),
                full_name=full_name.text(),
                role_id=int(role_box.currentData()),
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _change_role(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.information(self, tr("settings.title"), tr("settings.select_user"))
            return
        db = self._container.create_session()
        try:
            roles = SettingsService(db).list_roles()
        finally:
            db.close()
        labels = [r.name for r in roles]
        choice, ok = QInputDialog.getItem(
            self, tr("settings.user_change_role"), tr("settings.role"), labels, 0, False
        )
        if not ok:
            return
        role_id = roles[labels.index(choice)].id
        db = self._container.create_session()
        try:
            SettingsService(db).change_user_role(
                user_id, role_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _toggle_user(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.information(self, tr("settings.title"), tr("settings.select_user"))
            return
        db = self._container.create_session()
        try:
            users = SettingsService(db).list_users(self._session.user.company_id)
            current = next((u for u in users if u.id == user_id), None)
            if current is None:
                return
            SettingsService(db).set_user_active(
                user_id,
                is_active=not current.is_active,
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _show_roles(self) -> None:
        db = self._container.create_session()
        try:
            roles = SettingsService(db).list_roles()
        finally:
            db.close()
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("settings.roles_matrix"))
        dialog.resize(560, 420)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(
            [tr("settings.role"), tr("settings.permissions")]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, role in enumerate(roles):
            table.insertRow(row)
            perms = ", ".join(sorted(p.code for p in role.permissions))
            table.setItem(row, 0, QTableWidgetItem(role.name))
            table.setItem(row, 1, QTableWidgetItem(perms))
        layout.addWidget(table)
        close_btn = QPushButton(tr("common.close"))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def _activate_license(self) -> None:
        key, ok = QInputDialog.getText(
            self, tr("settings.license_activate"), tr("settings.license_key")
        )
        if not ok or not key.strip():
            return
        db = self._container.create_session()
        try:
            from app.modules.license.services.license_service import LicenseService

            LicenseService(db).activate(
                self._session.user.company_id,
                key,
                actor_id=self._session.user_id,
            )
            db.commit()
            QMessageBox.information(self, tr("settings.title"), tr("settings.license_ok"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.reload()

    def _save_shell_prefs(self) -> None:
        from app.ui.shell.shell_prefs import ShellPrefs, save_shell_prefs

        save_shell_prefs(ShellPrefs(idle_lock_minutes=self._idle_minutes.value()))
        QMessageBox.information(self, tr("settings.title"), tr("settings.idle_saved"))

    def _add_branch(self) -> None:
        code, ok = QInputDialog.getText(self, tr("branches.add"), tr("branches.code"))
        if not ok or not code.strip():
            return
        name, ok = QInputDialog.getText(self, tr("branches.add"), tr("branches.name"))
        if not ok or not name.strip():
            return
        db = self._container.create_session()
        try:
            from app.modules.branches.services.branch_service import (
                BranchCreateSchema,
                BranchService,
            )

            BranchService(db).create_branch(
                self._session.user.company_id,
                BranchCreateSchema(code=code, name=name),
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), str(exc))
            return
        finally:
            db.close()
        self.reload()
