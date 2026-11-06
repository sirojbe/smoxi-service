"""Reception desk — tezkor qabul (asosiy maydonlar + ixtiyoriy qoʻshimcha)."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.config.constants import DEFAULT_PHONE_PREFIX, DEFAULT_SERVICE_PRICE
from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.reception.services.quick_intake_service import (
    QuickIntakeSchema,
    QuickIntakeService,
)
from app.modules.reception.views.bot_link_dialog import BotLinkQrDialog
from app.modules.reception.views.product_dialogs import (
    PickedProduct,
    ProductFormDialog,
    ProductPickDialog,
)
from app.modules.work_orders.schemas.work_order_schema import WorkOrderPartSchema
from app.ui.widgets.number_stepper import NumberStepper


def _money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _field(label: str, widget: QWidget, *, required: bool = False) -> QWidget:
    """Label above control — enterprise form row."""
    box = QWidget()
    box.setObjectName("FieldBlock")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    caption = QLabel(f"{label} *" if required else label)
    caption.setObjectName("FieldLabel")
    layout.addWidget(caption)
    layout.addWidget(widget)
    return box


class ReceptionPage(QWidget):
    """Tezkor qabul: asosiy 4–5 maydon; qolgani «Qoʻshimcha»da."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._build_ui()
        self._reset_defaults()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(4)
        header.addWidget(QLabel(tr("reception.title"), objectName="PageTitle"))
        header.addWidget(QLabel(tr("reception.subtitle"), objectName="PageSubtitle"))
        root.addLayout(header)

        card = QFrame(objectName="IntakeCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 16)
        card_layout.setSpacing(14)

        self._phone = QLineEdit()
        self._phone.setPlaceholderText(tr("reception.phone_placeholder"))
        self._phone.setObjectName("IntakeField")
        self._phone.setMinimumHeight(42)

        self._name = QLineEdit()
        self._name.setPlaceholderText(tr("reception.name_placeholder"))
        self._name.setObjectName("IntakeField")
        self._name.setMinimumHeight(42)

        self._device = QLineEdit()
        self._device.setPlaceholderText(tr("reception.device_placeholder"))
        self._device.setObjectName("IntakeField")
        self._device.setMinimumHeight(42)

        self._problem = QTextEdit()
        self._problem.setPlaceholderText(tr("reception.problem_placeholder"))
        self._problem.setObjectName("IntakeField")
        self._problem.setMinimumHeight(86)
        self._problem.setMaximumHeight(120)

        self._estimate = NumberStepper(
            minimum=0,
            maximum=100_000_000,
            value=DEFAULT_SERVICE_PRICE,
            step=1_000,
            suffix=" soʻm",
            object_name="PriceInput",
            button_size=42,
        )
        self._estimate.setGroupSeparatorShown(True)
        self._estimate.setFixedWidth(280)
        self._estimate.valueChanged.connect(lambda _v: self._refresh_totals())

        primary = QGridLayout()
        primary.setHorizontalSpacing(14)
        primary.setVerticalSpacing(12)
        primary.addWidget(_field(tr("reception.phone"), self._phone, required=True), 0, 0)
        primary.addWidget(_field(tr("reception.customer_name"), self._name), 0, 1)
        primary.addWidget(
            _field(tr("reception.device_model"), self._device, required=True), 1, 0, 1, 2
        )
        primary.addWidget(
            _field(tr("reception.problem"), self._problem, required=True), 2, 0, 1, 2
        )

        estimate_wrap = QWidget()
        estimate_row = QHBoxLayout(estimate_wrap)
        estimate_row.setContentsMargins(0, 0, 0, 0)
        estimate_row.addWidget(_field(tr("reception.estimate"), self._estimate))
        estimate_row.addStretch(1)
        primary.addWidget(estimate_wrap, 3, 0, 1, 2)
        primary.setColumnStretch(0, 1)
        primary.setColumnStretch(1, 1)
        card_layout.addLayout(primary)

        self._more_btn = QToolButton()
        self._more_btn.setObjectName("LinkButton")
        self._more_btn.setCheckable(True)
        self._more_btn.setChecked(False)
        self._more_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._more_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._more_btn.setText(tr("reception.more_fields"))
        self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._more_btn.toggled.connect(self._toggle_more)
        card_layout.addWidget(self._more_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._more_panel = QFrame(objectName="IntakeMorePanel")
        self._more_panel.setVisible(False)
        more_layout = QVBoxLayout(self._more_panel)
        more_layout.setContentsMargins(14, 14, 14, 14)
        more_layout.setSpacing(12)

        self._brand = QLineEdit()
        self._brand.setPlaceholderText(tr("reception.brand_placeholder"))
        self._brand.setObjectName("IntakeField")
        self._brand.setMinimumHeight(40)
        self._serial = QLineEdit()
        self._serial.setPlaceholderText(tr("reception.serial_placeholder"))
        self._serial.setObjectName("IntakeField")
        self._serial.setMinimumHeight(40)
        self._accessories = QLineEdit()
        self._accessories.setPlaceholderText(tr("reception.accessories_placeholder"))
        self._accessories.setObjectName("IntakeField")
        self._accessories.setMinimumHeight(40)
        self._work_scope = QTextEdit()
        self._work_scope.setPlaceholderText(tr("reception.work_scope_placeholder"))
        self._work_scope.setObjectName("IntakeField")
        self._work_scope.setMaximumHeight(72)
        self._work_scope.setMinimumHeight(56)

        extra = QGridLayout()
        extra.setHorizontalSpacing(14)
        extra.setVerticalSpacing(12)
        extra.addWidget(_field(tr("reception.brand"), self._brand), 0, 0)
        extra.addWidget(_field(tr("cx.serial"), self._serial), 0, 1)
        extra.addWidget(_field(tr("cx.accessories"), self._accessories), 1, 0, 1, 2)
        extra.addWidget(_field(tr("reception.work_scope"), self._work_scope), 2, 0, 1, 2)
        extra.setColumnStretch(0, 1)
        extra.setColumnStretch(1, 1)
        more_layout.addLayout(extra)

        parts_header = QHBoxLayout()
        parts_header.setSpacing(8)
        parts_title = QLabel(tr("reception.parts_title"))
        parts_title.setObjectName("SectionTitle")
        parts_header.addWidget(parts_title)
        parts_header.addStretch()

        action_h = 42
        self._qty = NumberStepper(
            minimum=1,
            maximum=1_000,
            value=1,
            step=1,
            button_size=action_h,
        )
        self._qty.setFixedWidth(156)
        self._qty.setToolTip(tr("reception.part_qty"))
        self._qty.valueChanged.connect(self._apply_qty_to_selected)
        parts_header.addWidget(QLabel(tr("reception.part_qty"), objectName="FieldLabel"))
        parts_header.addWidget(self._qty)

        add_part_btn = QPushButton(tr("reception.part_add"))
        add_part_btn.setObjectName("PrimaryButton")
        add_part_btn.setFixedHeight(action_h)
        add_part_btn.clicked.connect(self._open_product_picker)
        edit_part_btn = QPushButton(tr("reception.product_edit"))
        edit_part_btn.setFixedHeight(action_h)
        edit_part_btn.clicked.connect(self._edit_selected_part)
        remove_part_btn = QPushButton(tr("reception.part_remove"))
        remove_part_btn.setFixedHeight(action_h)
        remove_part_btn.clicked.connect(self._remove_selected_part)
        parts_header.addWidget(add_part_btn)
        parts_header.addWidget(edit_part_btn)
        parts_header.addWidget(remove_part_btn)
        more_layout.addLayout(parts_header)

        self._parts = QTableWidget(0, 4)
        self._parts.setObjectName("IntakePartsTable")
        self._parts.setHorizontalHeaderLabels(
            [
                tr("reception.part_name"),
                tr("reception.part_cost"),
                tr("reception.part_sale"),
                tr("reception.part_qty"),
            ]
        )
        header = self._parts.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._parts.setColumnWidth(3, 90)
        self._parts.setMinimumHeight(110)
        self._parts.setMaximumHeight(160)
        self._parts.setAlternatingRowColors(True)
        self._parts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._parts.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._parts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._parts.verticalHeader().setVisible(False)
        self._parts.setShowGrid(True)
        more_layout.addWidget(self._parts)
        card_layout.addWidget(self._more_panel)

        footer = QFrame(objectName="IntakeFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)
        footer_layout.setSpacing(12)

        totals_col = QVBoxLayout()
        totals_col.setSpacing(2)
        self._expense_label = QLabel()
        self._expense_label.setObjectName("HintLabel")
        self._total_label = QLabel()
        self._total_label.setObjectName("TotalValue")
        totals_col.addWidget(self._expense_label)
        totals_col.addWidget(self._total_label)
        footer_layout.addLayout(totals_col)
        footer_layout.addStretch()

        clear_btn = QPushButton(tr("reception.clear"))
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(self._clear_form)
        create_btn = QPushButton(tr("reception.create"))
        create_btn.setObjectName("AccentButton")
        create_btn.setMinimumHeight(40)
        create_btn.setMinimumWidth(160)
        create_btn.setDefault(True)
        create_btn.clicked.connect(self._create)
        footer_layout.addWidget(clear_btn)
        footer_layout.addWidget(create_btn)
        card_layout.addWidget(footer)
        root.addWidget(card)

        self._result = QLabel("")
        self._result.setObjectName("SuccessBanner")
        self._result.setWordWrap(True)
        self._result.hide()
        root.addWidget(self._result)

        tip = QLabel(tr("reception.telegram_tip"))
        tip.setObjectName("InfoBanner")
        tip.setWordWrap(True)
        root.addWidget(tip)
        root.addStretch()

        self._parts.itemSelectionChanged.connect(self._on_part_selection)

    def _toggle_more(self, expanded: bool) -> None:
        self._more_panel.setVisible(expanded)
        self._more_btn.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._more_btn.setText(
            tr("reception.more_fields_hide") if expanded else tr("reception.more_fields")
        )

    def _reset_defaults(self) -> None:
        self._phone.setText(DEFAULT_PHONE_PREFIX)
        self._phone.setCursorPosition(len(DEFAULT_PHONE_PREFIX))
        self._estimate.setValue(DEFAULT_SERVICE_PRICE)
        self._qty.setValue(1)
        self._refresh_totals()

    def _open_product_picker(self) -> None:
        dialog = ProductPickDialog(self, container=self._container, session=self._session)
        if dialog.exec() != ProductPickDialog.DialogCode.Accepted or dialog.selected is None:
            return
        self._append_product(dialog.selected, quantity=self._qty.value())

    def _append_product(self, item: PickedProduct, *, quantity: int = 1) -> None:
        for row in range(self._parts.rowCount()):
            name_item = self._parts.item(row, 0)
            if name_item is None:
                continue
            existing_id = name_item.data(Qt.ItemDataRole.UserRole)
            if existing_id == item.id:
                qty_item = self._parts.item(row, 3)
                current = int(qty_item.text()) if qty_item else 1
                qty_item = QTableWidgetItem(str(current + quantity))
                qty_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._parts.setItem(row, 3, qty_item)
                self._parts.selectRow(row)
                self._refresh_totals()
                return

        row = self._parts.rowCount()
        self._parts.insertRow(row)
        name_item = QTableWidgetItem(item.name)
        name_item.setData(Qt.ItemDataRole.UserRole, item.id)
        self._parts.setItem(row, 0, name_item)
        for col, value in ((1, item.purchase_price), (2, item.sale_price), (3, quantity)):
            cell = QTableWidgetItem(_money(value) if col < 3 else str(value))
            cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._parts.setItem(row, col, cell)
        self._parts.selectRow(row)
        self._refresh_totals()

    def _selected_row(self) -> int | None:
        rows = self._parts.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _on_part_selection(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        qty_item = self._parts.item(row, 3)
        try:
            self._qty.blockSignals(True)
            self._qty.setValue(max(int(qty_item.text()) if qty_item else 1, 1))
        finally:
            self._qty.blockSignals(False)

    def _apply_qty_to_selected(self, value: int) -> None:
        row = self._selected_row()
        if row is None:
            return
        cell = QTableWidgetItem(str(value))
        cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._parts.setItem(row, 3, cell)
        self._refresh_totals()

    def _edit_selected_part(self) -> None:
        row = self._selected_row()
        if row is None:
            QMessageBox.information(
                self, tr("reception.parts_title"), tr("reception.product_select_first")
            )
            return
        name_item = self._parts.item(row, 0)
        item_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        if item_id is None:
            return
        snapshot = PickedProduct(
            id=int(item_id),
            name=name_item.text() if name_item else "",
            purchase_price=self._cell_int(row, 1),
            sale_price=self._cell_int(row, 2),
            quantity_on_hand=0,
        )
        dialog = ProductFormDialog(self, snapshot=snapshot)
        if dialog.exec() != ProductFormDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            updated = dialog.apply_to_service(
                InventoryService(db),
                self._session.user.company_id,
                actor_id=self._session.user_id,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        qty = self._cell_int(row, 3) or 1
        self._parts.item(row, 0).setText(updated.name)
        self._parts.item(row, 0).setData(Qt.ItemDataRole.UserRole, updated.id)
        for col, value in ((1, updated.purchase_price), (2, updated.sale_price)):
            cell = QTableWidgetItem(_money(value))
            cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._parts.setItem(row, col, cell)
        qty_cell = QTableWidgetItem(str(qty))
        qty_cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._parts.setItem(row, 3, qty_cell)
        self._refresh_totals()

    def _remove_selected_part(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._parts.removeRow(row)
        self._refresh_totals()

    def _collect_parts(self) -> list[WorkOrderPartSchema]:
        parts: list[WorkOrderPartSchema] = []
        for row in range(self._parts.rowCount()):
            name_item = self._parts.item(row, 0)
            name = (name_item.text() if name_item else "").strip()
            if not name:
                continue
            item_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
            cost = self._cell_int(row, 1)
            sale = self._cell_int(row, 2)
            qty = max(self._cell_int(row, 3), 1)
            parts.append(
                WorkOrderPartSchema(
                    name=name,
                    cost_price=cost,
                    sale_price=sale,
                    quantity=qty,
                    inventory_item_id=int(item_id) if item_id is not None else None,
                )
            )
        return parts

    def _cell_int(self, row: int, col: int) -> int:
        item = self._parts.item(row, col)
        raw = (item.text() if item else "0").replace(" ", "").replace(",", "")
        try:
            return max(int(raw), 0)
        except ValueError:
            return 0

    def _refresh_totals(self) -> None:
        parts = self._collect_parts()
        expense = sum(p.quantity * p.cost_price for p in parts)
        parts_sale = sum(p.quantity * p.sale_price for p in parts)
        service = self._estimate.value()
        total = service + parts_sale
        self._expense_label.setText(tr("reception.expense_auto", amount=_money(expense)))
        self._total_label.setText(tr("reception.customer_total", amount=_money(total)))

    def _clear_form(self, *, keep_result: bool = False) -> None:
        self._name.clear()
        self._device.clear()
        self._brand.clear()
        self._problem.clear()
        self._work_scope.clear()
        self._serial.clear()
        self._accessories.clear()
        self._parts.setRowCount(0)
        if not keep_result:
            self._result.hide()
        self._reset_defaults()

    def _offer_bot_link(self, bot_link: str, *, work_order_number: str) -> None:
        """Show QR — phone scan opens Telegram bot with auto /start."""
        BotLinkQrDialog(
            self,
            bot_link=bot_link,
            work_order_number=work_order_number,
        ).exec()

    def _create(self) -> None:
        self._refresh_totals()
        parts = self._collect_parts()
        data = {
            "phone": self._phone.text(),
            "display_name": self._name.text(),
            "device_model": self._device.text(),
            "device_brand": self._brand.text(),
            "serial_number": self._serial.text(),
            "accessories": self._accessories.text(),
            "problem_description": self._problem.toPlainText(),
            "work_scope": self._work_scope.toPlainText(),
            "estimated_cost": self._estimate.value() or DEFAULT_SERVICE_PRICE,
            "parts": [p.model_dump() for p in parts],
        }
        try:
            payload = QuickIntakeSchema.model_validate(data)
        except PydanticValidationError as exc:
            QMessageBox.warning(self, tr("common.error"), str(exc.errors()[0].get("msg")))
            return

        db = self._container.create_session()
        try:
            result = QuickIntakeService(db).intake(
                self._session.user.company_id,
                payload,
                actor_id=self._session.user_id,
                branch_id=self._session.active_branch_id,
            )
            db.commit()
            tg = (
                tr("reception.telegram_ok")
                if result.telegram_sent
                else tr("reception.telegram_pending")
            )
            link_line = ""
            if result.bot_link and not result.telegram_sent:
                link_line = "\n" + tr("reception.bot_link", link=result.bot_link)
            self._clear_form(keep_result=True)
            self._result.setText(
                tr(
                    "reception.created_rich",
                    number=result.work_order.number,
                    customer_id=result.customer.id,
                    phone=result.customer.phone,
                    telegram=tg,
                )
                + "\n"
                + tr("reception.expense_auto", amount=_money(result.expense_total))
                + " · "
                + tr("reception.customer_total", amount=_money(result.customer_total))
                + link_line
            )
            self._result.show()
            if result.bot_link and not result.telegram_sent:
                self._offer_bot_link(
                    result.bot_link,
                    work_order_number=result.work_order.number,
                )
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        except Exception as exc:  # noqa: BLE001 — never show traceback to user
            db.rollback()
            message = str(exc)
            if "UNIQUE" in message.upper() and "phone" in message.lower():
                message = tr("reception.phone_exists")
            else:
                message = tr("common.unexpected_error")
            QMessageBox.warning(self, tr("common.error"), message)
        finally:
            db.close()
