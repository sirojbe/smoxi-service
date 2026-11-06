"""Work orders list page with status transitions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
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
from app.modules.customers.repositories.customer_repository import CustomerRepository
from app.modules.customers.repositories.device_repository import DeviceRepository
from app.modules.cx.views.cx_hub_dialog import CxHubDialog
from app.modules.cx.views.timeline_dialog import CxTimelineDialog
from app.modules.technicians.services.technician_service import TechnicianService
from app.modules.work_orders.models.status import (
    WorkOrderStatus,
    priority_label,
    status_label,
)
from app.modules.work_orders.models.work_order import WorkOrder
from app.modules.work_orders.schemas.work_order_schema import WorkOrderStatusChangeSchema
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.ui.widgets.toast import show_toast


class StatusChangeDialog(QDialog):
    """Dialog to pick next status and optional note."""

    def __init__(
        self,
        parent: QWidget,
        *,
        current_status: str,
        allowed: list[WorkOrderStatus],
    ) -> None:
        super().__init__(parent)
        self._payload: WorkOrderStatusChangeSchema | None = None
        self.setWindowTitle(tr("work_orders.change_status"))
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow(tr("work_orders.current_status"), QLabel(status_label(current_status)))
        self._status = QComboBox()
        for item in allowed:
            self._status.addItem(status_label(item), item.value)
        self._note = QTextEdit()
        self._note.setMaximumHeight(80)
        form.addRow(tr("work_orders.new_status"), self._status)
        form.addRow(tr("work_orders.status_note"), self._note)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def payload(self) -> WorkOrderStatusChangeSchema | None:
        return self._payload

    def _save(self) -> None:
        self._payload = WorkOrderStatusChangeSchema(
            to_status=self._status.currentData(),
            note=self._note.toPlainText(),
        )
        self.accept()


class AssignTechnicianDialog(QDialog):
    """Assign or clear technician on a work order."""

    def __init__(
        self,
        parent: QWidget,
        *,
        technicians: list[tuple[int, str]],
        current_id: int | None,
    ) -> None:
        super().__init__(parent)
        self.selected_id: int | None = current_id
        self.setWindowTitle(tr("work_orders.assign_technician"))
        layout = QVBoxLayout(self)
        self._combo = QComboBox()
        self._combo.addItem(tr("work_orders.no_technician"), None)
        for tech_id, label in technicians:
            self._combo.addItem(label, tech_id)
        if current_id is not None:
            index = self._combo.findData(current_id)
            if index >= 0:
                self._combo.setCurrentIndex(index)
        layout.addWidget(self._combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        self.selected_id = self._combo.currentData()
        self.accept()


class WorkOrdersPage(QWidget):
    """Work order list and status management."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._orders: list[WorkOrder] = []
        self._customer_names: dict[int, str] = {}
        self._device_labels: dict[int, str] = {}
        self._technician_names: dict[int, str] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("work_orders.title"), objectName="PageTitle"))

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("work_orders.search_placeholder"))
        self._search.returnPressed.connect(self.refresh)
        self._status_filter = QComboBox()
        self._status_filter.addItem(tr("work_orders.active_only"), None)
        for status in WorkOrderStatus:
            self._status_filter.addItem(status_label(status), status.value)
        self._status_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        self._all_branches = QCheckBox(tr("work_orders.all_branches"))
        self._all_branches.stateChanged.connect(lambda _s: self.refresh())
        search_btn = QPushButton(tr("common.search"))
        search_btn.clicked.connect(self.refresh)
        refresh_btn = QPushButton(tr("common.refresh"))
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._search, stretch=1)
        toolbar.addWidget(self._status_filter)
        toolbar.addWidget(self._all_branches)
        toolbar.addWidget(search_btn)
        toolbar.addWidget(refresh_btn)
        root.addLayout(toolbar)

        hint = QLabel(tr("work_orders.context_hint"))
        hint.setObjectName("HintLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            [
                tr("work_orders.number"),
                tr("work_orders.customer"),
                tr("work_orders.device"),
                tr("work_orders.technician"),
                tr("work_orders.status"),
                tr("work_orders.priority"),
                tr("work_orders.problem"),
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._open_row_menu)
        self._table.doubleClicked.connect(lambda _idx: self._change_status())
        root.addWidget(self._table, stretch=1)
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        """Function-key hotkeys for the selected work order (F5 = refresh)."""

        def _bind(key: str, label: str, slot) -> QAction:
            action = QAction(label, self)
            action.setShortcut(QKeySequence(key))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.triggered.connect(slot)
            self.addAction(action)
            return action

        self._act_refresh = _bind("F5", tr("common.refresh"), self.refresh)
        self._act_status = _bind(
            "F6", tr("work_orders.change_status"), self._change_status
        )
        self._act_repair = _bind(
            "F7",
            tr("work_orders.quick_repairing"),
            lambda: self._quick_status(
                WorkOrderStatus.REPAIRING.value, "Tezkor: taʼmirlash"
            ),
        )
        self._act_parts = _bind(
            "F8",
            tr("work_orders.quick_waiting_parts"),
            lambda: self._quick_status(
                WorkOrderStatus.WAITING_PARTS.value, "Tezkor: ehtiyot qism"
            ),
        )
        self._act_ready = _bind("F9", tr("work_orders.quick_ready"), self._mark_ready)
        self._act_deliver = _bind(
            "F10", tr("work_orders.quick_deliver"), self._mark_delivered
        )
        self._act_assign = _bind(
            "F11", tr("work_orders.assign_technician"), self._assign_technician
        )
        self._act_history = _bind("F12", tr("work_orders.history"), self._show_history)

        # Delete/Ctrl+Delete on the table only — so search fields keep normal Delete.
        def _bind_table(key: str, label: str, slot) -> QAction:
            action = QAction(label, self._table)
            action.setShortcut(QKeySequence(key))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.triggered.connect(slot)
            self._table.addAction(action)
            return action

        self._act_cancel = _bind_table(
            "Delete", tr("work_orders.cancel"), self._cancel_order
        )
        self._act_delete = _bind_table(
            "Ctrl+Delete", tr("work_orders.delete"), self._delete_order
        )

    def _open_row_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if index.isValid():
            self._table.selectRow(index.row())
        if self._selected_id() is None:
            return

        menu = QMenu(self)
        for action in (
            self._act_status,
            None,
            self._act_repair,
            self._act_parts,
            self._act_ready,
            self._act_deliver,
            None,
            self._act_assign,
            self._act_history,
        ):
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)

        menu.addAction(tr("cx.hub_button"), self._show_cx_hub)
        menu.addSeparator()
        menu.addAction(self._act_cancel)
        menu.addAction(self._act_delete)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def refresh(self) -> None:
        """Reload work orders."""
        query = self._search.text().strip() or None
        status = self._status_filter.currentData()
        db = self._container.create_session()
        try:
            service = WorkOrderService(db)
            self._orders = service.list_work_orders(
                self._session.user.company_id,
                query=query,
                status=status,
                branch_id=(
                    None
                    if self._all_branches.isChecked()
                    else self._session.active_branch_id
                ),
            )
            self._customer_names = {
                c.id: c.display_name
                for c in CustomerRepository(db).list_all()
                if c.company_id == self._session.user.company_id
            }
            self._device_labels = {
                d.id: d.display_label
                for d in DeviceRepository(db).list_all()
                if d.company_id == self._session.user.company_id
            }
            self._technician_names = {
                t.id: t.full_name
                for t in TechnicianService(db).list_technicians(self._session.user.company_id)
            }
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            self._orders = []
        finally:
            db.close()
        self._fill_table()

    def focus_entity(self, entity_id: object) -> None:
        """Select a work order by id (Global Search)."""
        try:
            order_id = int(entity_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        self._search.clear()
        self._status_filter.setCurrentIndex(0)
        self._all_branches.setChecked(True)
        self.refresh()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and int(item.data(Qt.ItemDataRole.UserRole)) == order_id:
                self._table.selectRow(row)
                self._table.scrollToItem(item)
                return

    def _fill_table(self) -> None:
        self._table.setRowCount(0)
        for row, order in enumerate(self._orders):
            self._table.insertRow(row)
            tech_name = self._technician_names.get(order.technician_id or -1, "—")
            values = [
                order.number,
                self._customer_names.get(order.customer_id, str(order.customer_id)),
                self._device_labels.get(order.device_id or -1, "—"),
                tech_name,
                status_label(order.status),
                priority_label(order.priority),
                order.problem_description[:80],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, order.id)
                self._table.setItem(row, col, item)

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _quick_status(self, to_status: str, note: str) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        db = self._container.create_session()
        try:
            service = WorkOrderService(db)
            order = service.get_work_order(work_order_id)
            allowed = {s.value for s in service.available_transitions(work_order_id)}
            # Allow multi-step auto path: APPROVED → target, or direct if allowed.
            if to_status not in allowed:
                if (
                    order.status == WorkOrderStatus.WAITING_CUSTOMER_APPROVAL.value
                    and WorkOrderStatus.APPROVED.value in allowed
                ):
                    service.change_status(
                        work_order_id,
                        WorkOrderStatusChangeSchema(
                            to_status=WorkOrderStatus.APPROVED.value,
                            note=note,
                        ),
                        actor_id=self._session.user_id,
                        auto_advance=False,
                    )
                    order = service.get_work_order(work_order_id)
                    allowed = {s.value for s in service.available_transitions(work_order_id)}
                if to_status not in allowed:
                    raise AppError(
                        tr(
                            "work_orders.quick_not_allowed",
                            status=status_label(to_status),
                        )
                    )
            service.quick_set_status(
                work_order_id,
                to_status,
                actor_id=self._session.user_id,
                note=note,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()

    def _mark_ready(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        db = self._container.create_session()
        try:
            result = WorkOrderService(db).mark_ready(
                work_order_id,
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
        reason_key = {
            "sent": "work_orders.ready_telegram_ok",
            "no_token": "work_orders.ready_telegram_no_token",
            "no_chat": "work_orders.ready_telegram_no_chat",
            "already_ready": "work_orders.ready_already",
            "skipped": "work_orders.ready_telegram_skip",
        }.get(result.telegram_reason, "work_orders.ready_telegram_skip")
        show_toast(self, tr(reason_key, number=result.work_order.number))

    def _mark_delivered(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return

        db = self._container.create_session()
        try:
            service = WorkOrderService(db)
            order = service.get_work_order(work_order_id)
            unpaid = service.unpaid_balance_for_work_order(work_order_id)
            allow_unpaid = False
            if unpaid > 0:
                answer = QMessageBox.question(
                    self,
                    tr("work_orders.quick_deliver"),
                    tr(
                        "work_orders.deliver_unpaid_confirm",
                        number=order.number,
                        amount=f"{unpaid:,}".replace(",", " "),
                    ),
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                allow_unpaid = True
            else:
                answer = QMessageBox.question(
                    self,
                    tr("work_orders.quick_deliver"),
                    tr("work_orders.deliver_confirm", number=order.number),
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

            result = service.mark_delivered(
                work_order_id,
                actor_id=self._session.user_id,
                allow_unpaid=allow_unpaid,
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
        reason_key = {
            "sent": "work_orders.deliver_telegram_ok",
            "no_token": "work_orders.deliver_telegram_no_token",
            "no_chat": "work_orders.deliver_telegram_no_chat",
            "already_delivered": "work_orders.deliver_already",
            "skipped": "work_orders.deliver_telegram_skip",
        }.get(result.telegram_reason, "work_orders.deliver_telegram_skip")
        show_toast(self, tr(reason_key, number=result.work_order.number))

    def _cancel_order(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        note, ok = QInputDialog.getMultiLineText(
            self,
            tr("work_orders.cancel"),
            tr("work_orders.cancel_note_prompt"),
            tr("work_orders.cancel_note_default"),
        )
        if not ok:
            return
        if not note.strip():
            QMessageBox.warning(self, tr("common.error"), tr("work_orders.cancel_note_required"))
            return
        db = self._container.create_session()
        try:
            WorkOrderService(db).cancel_work_order(
                work_order_id,
                note=note.strip(),
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
        QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.cancel_done"))

    def _delete_order(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        answer = QMessageBox.question(
            self,
            tr("work_orders.delete"),
            tr("work_orders.delete_confirm"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            WorkOrderService(db).soft_delete_work_order(
                work_order_id,
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
        QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.delete_done"))

    def _change_status(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        db = self._container.create_session()
        try:
            service = WorkOrderService(db)
            work_order = service.get_work_order(work_order_id)
            allowed = service.available_transitions(work_order_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        if not allowed:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.no_transitions"))
            return

        dialog = StatusChangeDialog(self, current_status=work_order.status, allowed=allowed)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return

        db = self._container.create_session()
        try:
            WorkOrderService(db).change_status(
                work_order_id,
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

    def _assign_technician(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        db = self._container.create_session()
        try:
            order = WorkOrderService(db).get_work_order(work_order_id)
            techs = [
                (t.id, f"{t.full_name} ({t.code})")
                for t in TechnicianService(db).list_technicians(self._session.user.company_id)
                if t.is_active
            ]
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        dialog = AssignTechnicianDialog(
            self,
            technicians=techs,
            current_id=order.technician_id,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        db = self._container.create_session()
        try:
            TechnicianService(db).assign_to_work_order(
                work_order_id,
                dialog.selected_id,
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
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        dialog = CxTimelineDialog(self, self._container, work_order_id)
        dialog.exec()

    def _show_cx_hub(self) -> None:
        work_order_id = self._selected_id()
        if work_order_id is None:
            QMessageBox.information(self, tr("work_orders.title"), tr("work_orders.select_first"))
            return
        CxHubDialog(self, self._container, self._session, work_order_id).exec()
