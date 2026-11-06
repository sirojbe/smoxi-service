"""Product pick / create / edit dialogs for reception (warehouse catalog)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
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


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


@dataclass(frozen=True, slots=True)
class PickedProduct:
    """Detached product snapshot for reception (safe after DB session closes)."""

    id: int
    name: str
    purchase_price: int
    sale_price: int
    quantity_on_hand: int


def _snapshot(item: InventoryItem) -> PickedProduct:
    return PickedProduct(
        id=int(item.id),
        name=str(item.name),
        purchase_price=int(item.purchase_price or 0),
        sale_price=int(item.sale_price or 0),
        quantity_on_hand=int(item.quantity_on_hand or 0),
    )


class ProductFormDialog(QDialog):
    """Create or edit a catalog product (saved in inventory)."""

    def __init__(
        self,
        parent=None,
        *,
        item: InventoryItem | None = None,
        snapshot: PickedProduct | None = None,
    ) -> None:
        super().__init__(parent)
        self._item = item
        self._item_id = item.id if item is not None else (snapshot.id if snapshot else None)
        self._saved: PickedProduct | None = None
        self.setWindowTitle(
            tr("reception.product_edit") if self._item_id else tr("reception.product_new")
        )
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._cost = QSpinBox()
        self._cost.setRange(0, 1_000_000_000)
        self._cost.setSuffix(" soʻm")
        self._cost.setGroupSeparatorShown(True)
        self._sale = QSpinBox()
        self._sale.setRange(0, 1_000_000_000)
        self._sale.setSuffix(" soʻm")
        self._sale.setGroupSeparatorShown(True)
        form.addRow(tr("reception.part_name"), self._name)
        form.addRow(tr("reception.part_cost"), self._cost)
        form.addRow(tr("reception.part_sale"), self._sale)
        layout.addLayout(form)
        if item is not None:
            self._name.setText(item.name)
            self._cost.setValue(item.purchase_price)
            self._sale.setValue(item.sale_price)
        elif snapshot is not None:
            self._name.setText(snapshot.name)
            self._cost.setValue(snapshot.purchase_price)
            self._sale.setValue(snapshot.sale_price)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def product_name(self) -> str:
        return self._name.text().strip()

    @property
    def cost_price(self) -> int:
        return self._cost.value()

    @property
    def sale_price(self) -> int:
        return self._sale.value()

    @property
    def saved_item(self) -> PickedProduct | None:
        return self._saved

    def apply_to_service(
        self,
        service: InventoryService,
        company_id: int,
        *,
        actor_id: int | None,
    ) -> PickedProduct:
        name = self.product_name
        if not name:
            raise AppError("Mahsulot nomi majburiy.")
        if self._item_id is None:
            sku = f"PRT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                payload = InventoryItemCreateSchema(
                    sku=sku,
                    name=name,
                    purchase_price=self.cost_price,
                    sale_price=self.sale_price,
                    quantity_on_hand=0,
                    category="qabul",
                )
            except PydanticValidationError as exc:
                raise AppError(str(exc.errors()[0].get("msg"))) from exc
            created = service.create_item(company_id, payload, actor_id=actor_id)
            self._saved = _snapshot(created)
            return self._saved
        existing = service.get_item(self._item_id)
        try:
            payload = InventoryItemUpdateSchema(
                sku=existing.sku,
                name=name,
                category=existing.category,
                barcode=existing.barcode,
                unit=existing.unit,
                quantity_on_hand=existing.quantity_on_hand,
                min_quantity=existing.min_quantity,
                purchase_price=self.cost_price,
                sale_price=self.sale_price,
                notes=existing.notes,
                is_active=True,
            )
        except PydanticValidationError as exc:
            raise AppError(str(exc.errors()[0].get("msg"))) from exc
        updated = service.update_item(existing.id, payload, actor_id=actor_id)
        self._saved = _snapshot(updated)
        return self._saved


class ProductPickDialog(QDialog):
    """Pick a warehouse product (name + prices) or create a new catalog item."""

    def __init__(
        self,
        parent,
        *,
        container: ServiceContainer,
        session: DesktopSession,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._session = session
        self._items: list[PickedProduct] = []
        self.selected: PickedProduct | None = None
        self.setWindowTitle(tr("reception.product_pick"))
        self.setMinimumSize(560, 460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("reception.product_pick_hint")))

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("reception.product_search"))
        self._search.textChanged.connect(self._reload)
        search_row.addWidget(self._search, stretch=1)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self._reload)
        search_row.addWidget(refresh_btn)
        new_btn = QPushButton(tr("reception.product_new"))
        new_btn.setObjectName("PrimaryButton")
        new_btn.clicked.connect(self._create_new)
        search_row.addWidget(new_btn)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            [
                tr("reception.part_name"),
                tr("reception.part_cost"),
                tr("reception.part_sale"),
                tr("reception.product_stock"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.doubleClicked.connect(self._choose_current)
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        edit_btn = QPushButton(tr("reception.product_edit"))
        edit_btn.clicked.connect(self._edit_selected)
        pick_btn = QPushButton(tr("reception.product_select"))
        pick_btn.setObjectName("AccentButton")
        pick_btn.clicked.connect(self._choose_current)
        cancel_btn = QPushButton(tr("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(edit_btn)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(pick_btn)
        layout.addLayout(buttons)
        self._reload()

    def _reload(self) -> None:
        query = self._search.text().strip() or None
        db = self._container.create_session()
        try:
            rows = InventoryService(db).list_items(
                self._session.user.company_id,
                query=query,
            )
            self._items = [_snapshot(i) for i in rows if i.is_active]
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._items = []
        finally:
            db.close()

        self._table.setRowCount(0)
        for product in self._items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            name_item = QTableWidgetItem(product.name)
            name_item.setData(Qt.ItemDataRole.UserRole, product.id)
            self._table.setItem(row, 0, name_item)
            for col, value in (
                (1, _money(product.purchase_price)),
                (2, _money(product.sale_price)),
                (3, str(product.quantity_on_hand)),
            ):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._table.setItem(row, col, cell)

    def _current_product(self) -> PickedProduct | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        product_id = int(item.data(Qt.ItemDataRole.UserRole))
        return next((p for p in self._items if p.id == product_id), None)

    def _choose_current(self) -> None:
        product = self._current_product()
        if product is None:
            QMessageBox.information(
                self, tr("reception.parts_title"), tr("reception.product_select_first")
            )
            return
        self.selected = product
        self.accept()

    def _create_new(self) -> None:
        dialog = ProductFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            product = dialog.apply_to_service(
                InventoryService(db),
                self._session.user.company_id,
                actor_id=self._session.user_id,
            )
            db.commit()
            self.selected = product
            self.accept()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _edit_selected(self) -> None:
        product = self._current_product()
        if product is None:
            QMessageBox.information(
                self, tr("reception.parts_title"), tr("reception.product_select_first")
            )
            return
        dialog = ProductFormDialog(self, snapshot=product)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            dialog.apply_to_service(
                InventoryService(db),
                self._session.user.company_id,
                actor_id=self._session.user_id,
            )
            db.commit()
            self._reload()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()
