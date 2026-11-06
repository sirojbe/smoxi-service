"""Automation rules management page."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.automation.models.rule import (
    ACTION_CALENDAR,
    ACTION_NOTIFY,
    TRIGGER_LOW_STOCK,
    TRIGGER_MANUAL,
    TRIGGER_WO_STATUS,
)
from app.modules.automation.schemas.rule_schema import (
    AutomationRuleCreateSchema,
    AutomationRuleUpdateSchema,
)
from app.modules.automation.services.automation_service import AutomationService


class RuleFormDialog(QDialog):
    def __init__(self, parent: QWidget, *, rule=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            tr("automation.edit") if rule else tr("automation.new")
        )
        self.payload: AutomationRuleCreateSchema | None = None
        form = QFormLayout(self)
        self._name = QLineEdit(rule.name if rule else "")
        self._desc = QTextEdit()
        self._desc.setPlainText(rule.description or "" if rule else "")
        self._desc.setMaximumHeight(70)
        self._trigger = QComboBox()
        for code, key in (
            (TRIGGER_MANUAL, "automation.trigger_manual"),
            (TRIGGER_WO_STATUS, "automation.trigger_wo_status"),
            (TRIGGER_LOW_STOCK, "automation.trigger_low_stock"),
        ):
            self._trigger.addItem(tr(key), code)
        if rule:
            idx = self._trigger.findData(rule.trigger_type)
            if idx >= 0:
                self._trigger.setCurrentIndex(idx)
        self._trigger_value = QLineEdit(rule.trigger_value or "" if rule else "")
        self._trigger_value.setPlaceholderText("ready / delivered …")
        self._action = QComboBox()
        for code, key in (
            (ACTION_NOTIFY, "automation.action_notify"),
            (ACTION_CALENDAR, "automation.action_calendar"),
        ):
            self._action.addItem(tr(key), code)
        if rule:
            idx = self._action.findData(rule.action_type)
            if idx >= 0:
                self._action.setCurrentIndex(idx)
        self._payload = QLineEdit(rule.action_payload or "" if rule else "")
        self._enabled = QCheckBox(tr("automation.enabled"))
        self._enabled.setChecked(True if rule is None else bool(rule.is_enabled))
        form.addRow(tr("automation.name"), self._name)
        form.addRow(tr("automation.description"), self._desc)
        form.addRow(tr("automation.trigger"), self._trigger)
        form.addRow(tr("automation.trigger_value"), self._trigger_value)
        form.addRow(tr("automation.action"), self._action)
        form.addRow(tr("automation.payload"), self._payload)
        form.addRow(self._enabled)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _ok(self) -> None:
        try:
            self.payload = AutomationRuleCreateSchema(
                name=self._name.text(),
                description=self._desc.toPlainText() or None,
                trigger_type=str(self._trigger.currentData()),
                trigger_value=self._trigger_value.text() or None,
                action_type=str(self._action.currentData()),
                action_payload=self._payload.text() or None,
                is_enabled=self._enabled.isChecked(),
            )
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0]["msg"]))
            return
        self.accept()


class AutomationPage(QWidget):
    """Rule list, enable/disable, test run, history."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._items: list = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("automation.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("automation.subtitle")))

        toolbar = QHBoxLayout()
        add_btn = QPushButton(tr("automation.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton(tr("automation.edit"))
        edit_btn.clicked.connect(self._edit)
        run_btn = QPushButton(tr("automation.run"))
        run_btn.clicked.connect(self._run)
        seed_btn = QPushButton(tr("automation.seed"))
        seed_btn.clicked.connect(self._seed)
        del_btn = QPushButton(tr("automation.delete"))
        del_btn.clicked.connect(self._delete)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        for b in (add_btn, edit_btn, run_btn, seed_btn, del_btn, refresh_btn):
            toolbar.addWidget(b)
        toolbar.addStretch()
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                tr("automation.name"),
                tr("automation.trigger"),
                tr("automation.action"),
                tr("automation.enabled"),
                tr("automation.runs"),
                tr("automation.last_run"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

        root.addWidget(QLabel(tr("automation.history")))
        self._history = QTableWidget(0, 4)
        self._history.setHorizontalHeaderLabels(
            [
                tr("automation.ran_at"),
                tr("automation.rule"),
                tr("automation.status"),
                tr("automation.message"),
            ]
        )
        self._history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history.horizontalHeader().setStretchLastSection(True)
        self._history.setMaximumHeight(200)
        root.addWidget(self._history)
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        db = self._container.create_session()
        try:
            svc = AutomationService(db)
            self._items = svc.list_rules(self._session.user.company_id)
            runs = svc.list_runs(self._session.user.company_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._table.setRowCount(0)
        for row, rule in enumerate(self._items):
            self._table.insertRow(row)
            values = [
                rule.name,
                f"{rule.trigger_type}"
                + (f"={rule.trigger_value}" if rule.trigger_value else ""),
                rule.action_type,
                tr("automation.enabled_yes") if rule.is_enabled else tr("automation.enabled_no"),
                str(rule.run_count),
                rule.last_run_at.strftime("%d.%m %H:%M") if rule.last_run_at else "—",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, rule.id)
                self._table.setItem(row, col, item)
        self._history.setRowCount(0)
        rule_names = {r.id: r.name for r in self._items}
        for row, run in enumerate(runs[:30]):
            self._history.insertRow(row)
            vals = [
                run.ran_at.strftime("%d.%m %H:%M") if run.ran_at else "",
                rule_names.get(run.rule_id, str(run.rule_id)),
                run.status,
                (run.message or "")[:80],
            ]
            for col, value in enumerate(vals):
                self._history.setItem(row, col, QTableWidgetItem(value))

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))

    def _add(self) -> None:
        dialog = RuleFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            AutomationService(db).create_rule(
                self._session.user.company_id,
                dialog.payload,
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _edit(self) -> None:
        rule_id = self._selected_id()
        if rule_id is None:
            QMessageBox.information(
                self, tr("automation.title"), tr("automation.select_first")
            )
            return
        rule = next((r for r in self._items if r.id == rule_id), None)
        dialog = RuleFormDialog(self, rule=rule)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            AutomationService(db).update_rule(
                rule_id,
                AutomationRuleUpdateSchema(**dialog.payload.model_dump()),
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _run(self) -> None:
        rule_id = self._selected_id()
        if rule_id is None:
            QMessageBox.information(
                self, tr("automation.title"), tr("automation.select_first")
            )
            return
        db = self._container.create_session()
        try:
            run = AutomationService(db).run_rule(
                rule_id, actor_id=self._session.user_id, context="Qoʻlda ishga tushirildi"
            )
            db.commit()
            QMessageBox.information(
                self,
                tr("automation.title"),
                tr("automation.run_result", status=run.status, message=run.message or ""),
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _seed(self) -> None:
        db = self._container.create_session()
        try:
            n = AutomationService(db).seed_defaults(
                self._session.user.company_id, actor_id=self._session.user_id
            )
            db.commit()
            QMessageBox.information(
                self, tr("automation.title"), tr("automation.seed_done", count=n)
            )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _delete(self) -> None:
        rule_id = self._selected_id()
        if rule_id is None:
            return
        if (
            QMessageBox.question(
                self, tr("automation.title"), tr("automation.delete_confirm")
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        db = self._container.create_session()
        try:
            AutomationService(db).soft_delete(
                rule_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
