"""Inventory items page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.inventory.models.item import InventoryItem
from app.modules.inventory.schemas.item_schema import (
    InventoryItemCreateSchema,
    InventoryItemUpdateSchema,
)
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.inventory.views.item_form_dialog import InventoryItemFormDialog
from app.modules.inventory.views.stock_adjust_dialog import StockAdjustDialog


class InventoryPage(QWidget):
    """Inventory list with stock operations."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._items: list[InventoryItem] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("inventory.title"), objectName="PageTitle"))

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("inventory.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        self._low_stock = QCheckBox(tr("inventory.low_stock_only"))
        self._low_stock.stateChanged.connect(self.refresh)
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        add_btn = QPushButton(tr("inventory.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_item)
        edit_btn = QPushButton(tr("inventory.edit"))
        edit_btn.clicked.connect(self._edit_item)
        adjust_btn = QPushButton(tr("inventory.adjust"))
        adjust_btn.clicked.connect(self._adjust_stock)
        history_btn = QPushButton(tr("inventory.history"))
        history_btn.clicked.connect(self._show_history)
        delete_btn = QPushButton(tr("inventory.delete"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_item)

        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(self._low_stock)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(adjust_btn)
        toolbar.addWidget(history_btn)
        toolbar.addWidget(delete_btn)
        root.addLayout(toolbar)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            [
                tr("inventory.sku"),
                tr("inventory.name"),
                tr("inventory.category"),
                tr("inventory.quantity"),
                tr("inventory.min_quantity"),
                tr("inventory.sale_price"),
                tr("inventory.status"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            service = InventoryService(db)
            self._items = service.list_items(
                self._session.user.company_id,
                query=query,
                low_stock_only=self._low_stock.isChecked(),
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._items = []
        finally:
            db.close()
        self._fill_table()

    def _fill_table(self) -> None:
        self._table.setRowCount(0)
        for row, item in enumerate(self._items):
            self._table.insertRow(row)
            status = tr("inventory.low_stock") if item.is_low_stock else tr("inventory.ok")
            values = [
                item.sku,
                item.name,
                item.category or "",
                str(item.quantity_on_hand),
                str(item.min_quantity),
                f"{item.sale_price:,}".replace(",", " "),
                status,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item.id)
                if item.is_low_stock:
                    cell.setForeground(Qt.GlobalColor.red)
                self._table.setItem(row, col, cell)

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        cell = self._table.item(rows[0].row(), 0)
        if cell is None:
            return None
        return int(cell.data(Qt.ItemDataRole.UserRole))

    def _add_item(self) -> None:
        dialog = InventoryItemFormDialog(self)
        if dialog.exec() != InventoryItemFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, InventoryItemCreateSchema)
        db = self._container.create_session()
        try:
            InventoryService(db).create_item(
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

    def _edit_item(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            QMessageBox.information(self, tr("inventory.title"), tr("inventory.select_first"))
            return
        db = self._container.create_session()
        try:
            item = InventoryService(db).get_item(item_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        dialog = InventoryItemFormDialog(self, item=item)
        if dialog.exec() != InventoryItemFormDialog.DialogCode.Accepted or dialog.payload is None:
            return
        assert isinstance(dialog.payload, InventoryItemUpdateSchema)
        db = self._container.create_session()
        try:
            InventoryService(db).update_item(
                item_id,
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

    def _adjust_stock(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            QMessageBox.information(self, tr("inventory.title"), tr("inventory.select_first"))
            return
        item = next((i for i in self._items if i.id == item_id), None)
        if item is None:
            return
        dialog = StockAdjustDialog(self, current_qty=item.quantity_on_hand)
        if dialog.exec() != StockAdjustDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).adjust_stock(
                item_id,
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

    def _show_history(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            QMessageBox.information(self, tr("inventory.title"), tr("inventory.select_first"))
            return
        db = self._container.create_session()
        try:
            movements = InventoryService(db).list_movements(item_id)
            if not movements:
                text = tr("inventory.no_history")
            else:
                lines = []
                for move in movements:
                    when = move.moved_at.strftime("%Y-%m-%d %H:%M")
                    reason = f" — {move.reason}" if move.reason else ""
                    lines.append(
                        f"{when}: {move.movement_type} {move.quantity_delta:+d} "
                        f"→ {move.quantity_after}{reason}"
                    )
                text = "\n".join(lines)
            QMessageBox.information(self, tr("inventory.history"), text)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _delete_item(self) -> None:
        item_id = self._selected_id()
        if item_id is None:
            QMessageBox.information(self, tr("inventory.title"), tr("inventory.select_first"))
            return
        answer = QMessageBox.question(self, tr("inventory.delete"), tr("inventory.delete_confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            InventoryService(db).delete_item(item_id, actor_id=self._session.user_id)
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
