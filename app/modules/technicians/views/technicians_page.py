"""Technicians list page."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.modules.technicians.models.technician import Technician
from app.modules.technicians.schemas.technician_schema import (
    TechnicianCreateSchema,
    TechnicianUpdateSchema,
)
from app.modules.technicians.services.technician_service import TechnicianService


class TechnicianFormDialog(QDialog):
    """Create/edit technician dialog."""

    def __init__(self, parent=None, *, technician: Technician | None = None) -> None:
        super().__init__(parent)
        self._technician = technician
        self._payload: TechnicianCreateSchema | TechnicianUpdateSchema | None = None
        self.setWindowTitle(
            tr("technicians.edit_title") if technician else tr("technicians.new_title")
        )
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._code = QLineEdit()
        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._skills = QLineEdit()
        self._available = QCheckBox(tr("technicians.available"))
        self._available.setChecked(True)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(70)
        form.addRow(tr("technicians.code"), self._code)
        form.addRow(tr("technicians.name"), self._name)
        form.addRow(tr("technicians.phone"), self._phone)
        form.addRow(tr("technicians.skills"), self._skills)
        form.addRow("", self._available)
        form.addRow(tr("technicians.notes"), self._notes)
        layout.addLayout(form)
        if technician is not None:
            self._code.setText(technician.code)
            self._name.setText(technician.full_name)
            self._phone.setText(technician.phone or "")
            self._skills.setText(technician.skills or "")
            self._available.setChecked(technician.is_available)
            self._notes.setPlainText(technician.notes or "")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> TechnicianCreateSchema | TechnicianUpdateSchema | None:
        return self._payload

    def _save(self) -> None:
        data = {
            "code": self._code.text(),
            "full_name": self._name.text(),
            "phone": self._phone.text(),
            "skills": self._skills.text(),
            "notes": self._notes.toPlainText(),
            "is_available": self._available.isChecked(),
        }
        try:
            if self._technician is None:
                self._payload = TechnicianCreateSchema.model_validate(data)
            else:
                self._payload = TechnicianUpdateSchema.model_validate(
                    {**data, "is_active": self._technician.is_active}
                )
            self.accept()
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))


class TechniciansPage(QWidget):
    """Technicians management page."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._items: list[Technician] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("technicians.title"), objectName="PageTitle"))
        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("technicians.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("technicians.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton(tr("technicians.edit"))
        edit_btn.clicked.connect(self._edit)
        delete_btn = QPushButton(tr("technicians.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(delete_btn)
        root.addLayout(toolbar)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                tr("technicians.code"),
                tr("technicians.name"),
                tr("technicians.phone"),
                tr("technicians.skills"),
                tr("technicians.status"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            self._items = TechnicianService(db).list_technicians(
                self._session.user.company_id,
                query=query,
            )
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._items = []
        finally:
            db.close()
        self._table.setRowCount(0)
        for row, tech in enumerate(self._items):
            self._table.insertRow(row)
            status = (
                tr("technicians.available")
                if tech.is_available
                else tr("technicians.busy")
            )
            values = [tech.code, tech.full_name, tech.phone or "", tech.skills or "", status]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, tech.id)
                self._table.setItem(row, col, item)

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))

    def _add(self) -> None:
        dialog = TechnicianFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, TechnicianCreateSchema)
        db = self._container.create_session()
        try:
            TechnicianService(db).create_technician(
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
        tech_id = self._selected_id()
        if tech_id is None:
            QMessageBox.information(self, tr("technicians.title"), tr("technicians.select_first"))
            return
        tech = next((t for t in self._items if t.id == tech_id), None)
        if tech is None:
            return
        dialog = TechnicianFormDialog(self, technician=tech)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, TechnicianUpdateSchema)
        db = self._container.create_session()
        try:
            TechnicianService(db).update_technician(
                tech_id,
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

    def _delete(self) -> None:
        tech_id = self._selected_id()
        if tech_id is None:
            QMessageBox.information(self, tr("technicians.title"), tr("technicians.select_first"))
            return
        if QMessageBox.question(self, tr("technicians.delete"), tr("technicians.delete_confirm")) != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            TechnicianService(db).delete_technician(tech_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
