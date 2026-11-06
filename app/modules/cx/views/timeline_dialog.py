"""CX timeline + QR dialog for a work order."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.qrcode_util import QrCodeError, qr_pixmap_from_text
from app.localization.translator import tr
from app.modules.cx.services.timeline_service import TimelineService
from app.modules.cx.services.wo_qr_service import WorkOrderQrService
from app.modules.work_orders.models.status import status_label
from app.modules.work_orders.services.work_order_service import WorkOrderService


class CxTimelineDialog(QDialog):
    """Show CX repair timeline and work-order QR (CX-A)."""

    def __init__(
        self,
        parent: QWidget,
        container: ServiceContainer,
        work_order_id: int,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._work_order_id = work_order_id
        self.setWindowTitle(tr("cx.timeline_title"))
        self.setMinimumSize(720, 480)

        main = QVBoxLayout(self)
        body = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel(tr("cx.timeline_heading")))
        self._header = QLabel("")
        self._header.setWordWrap(True)
        left.addWidget(self._header)
        self._list = QListWidget()
        left.addWidget(self._list, stretch=1)
        body.addLayout(left, stretch=3)

        right = QVBoxLayout()
        right.addWidget(QLabel(tr("cx.qr_heading")))
        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setMinimumSize(220, 220)
        self._qr_label.setStyleSheet(
            "background:#FFFFFF;border:1px solid #CBD5E1;border-radius:8px;"
        )
        right.addWidget(self._qr_label)
        self._payload = QLabel("")
        self._payload.setWordWrap(True)
        self._payload.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._payload.setObjectName("HintLabel")
        right.addWidget(self._payload)
        right.addStretch()
        body.addLayout(right, stretch=2)

        main.addLayout(body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText(tr("common.close"))
            close_btn.clicked.connect(self.accept)
        main.addWidget(buttons)

        self._load()

    def _load(self) -> None:
        db = self._container.create_session()
        try:
            work_order = WorkOrderService(db).get_work_order(self._work_order_id)
            timeline = TimelineService(db)
            timeline.ensure_seeded_from_status_history(work_order)
            payload = WorkOrderQrService(db).qr_payload_for(work_order)
            db.commit()

            self._header.setText(
                tr(
                    "cx.timeline_header",
                    number=work_order.number,
                    status=status_label(work_order.status),
                )
            )
            self._list.clear()
            events = timeline.list_events(work_order.id)
            if not events:
                self._list.addItem(tr("cx.timeline_empty"))
            else:
                for event in events:
                    when = ""
                    if event.created_at is not None and hasattr(
                        event.created_at, "strftime"
                    ):
                        when = event.created_at.strftime("%Y-%m-%d %H:%M")
                    note = f"\n{event.notes}" if event.notes else ""
                    status_bit = ""
                    if event.from_status or event.to_status:
                        frm = (
                            status_label(event.from_status)
                            if event.from_status
                            else "—"
                        )
                        to = (
                            status_label(event.to_status) if event.to_status else "—"
                        )
                        status_bit = f"\n{frm} → {to}"
                    text = f"{when}  ·  {event.title}{status_bit}{note}"
                    self._list.addItem(QListWidgetItem(text))

            self._payload.setText(payload)
            try:
                pixmap = qr_pixmap_from_text(payload, box_size=6, border=2)
                self._qr_label.setPixmap(
                    pixmap.scaled(
                        200,
                        200,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            except QrCodeError as exc:
                self._qr_label.setText(str(exc))
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()
