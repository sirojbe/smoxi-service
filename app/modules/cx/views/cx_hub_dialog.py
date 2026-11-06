"""CX hub dialog — media, signature, PDF, warranty, quote (CX-B/C/D/G)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.cx.services.intake_service import IntakeService
from app.modules.cx.services.media_service import MediaService
from app.modules.cx.services.quote_service import QuoteService
from app.modules.cx.services.warranty_service import WarrantyService
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository


class _SignaturePad(QWidget):
    """Simple mouse signature canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setStyleSheet("background:#FFFFFF;border:1px solid #94A3B8;")
        self._image = QImage(600, 160, QImage.Format.Format_RGB32)
        self._image.fill(Qt.GlobalColor.white)
        self._last: QPoint | None = None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._last = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._last is None:
            return
        painter = QPainter(self._image)
        pen = QPen(Qt.GlobalColor.black, 2)
        painter.setPen(pen)
        point = event.position().toPoint()
        sx = self._image.width() / max(self.width(), 1)
        sy = self._image.height() / max(self.height(), 1)
        p1 = QPoint(int(self._last.x() * sx), int(self._last.y() * sy))
        p2 = QPoint(int(point.x() * sx), int(point.y() * sy))
        painter.drawLine(p1, p2)
        painter.end()
        self._last = point
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._last = None

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawImage(self.rect(), self._image)

    def clear(self) -> None:
        self._image.fill(Qt.GlobalColor.white)
        self.update()

    def png_bytes(self) -> bytes:
        from PySide6.QtCore import QBuffer, QIODevice

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._image.save(buffer, "PNG")
        return bytes(buffer.data())


class CxHubDialog(QDialog):
    """Operate CX extras for one work order."""

    def __init__(
        self,
        parent: QWidget,
        container: ServiceContainer,
        session: DesktopSession,
        work_order_id: int,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._session = session
        self._work_order_id = work_order_id
        self.setWindowTitle(tr("cx.hub_title"))
        self.setMinimumSize(640, 560)
        root = QVBoxLayout(self)

        root.addWidget(QLabel(tr("cx.quote_heading")))
        quote_row = QHBoxLayout()
        quote_row.addWidget(QLabel(tr("cx.quote_amount")))
        self._quote_amount = QSpinBox()
        self._quote_amount.setRange(0, 100_000_000)
        self._quote_amount.setSingleStep(10_000)
        quote_row.addWidget(self._quote_amount)
        submit_quote = QPushButton(tr("cx.submit_quote"))
        submit_quote.setObjectName("PrimaryButton")
        submit_quote.clicked.connect(self._submit_quote)
        quote_row.addWidget(submit_quote)
        override_btn = QPushButton(tr("cx.admin_override"))
        override_btn.clicked.connect(self._admin_override)
        quote_row.addWidget(override_btn)
        root.addLayout(quote_row)

        self._media_list = QListWidget()
        root.addWidget(QLabel(tr("cx.media_heading")))
        root.addWidget(self._media_list)
        media_row = QHBoxLayout()
        add_photo = QPushButton(tr("cx.add_photo"))
        add_photo.clicked.connect(self._add_photo)
        add_video = QPushButton(tr("cx.add_video"))
        add_video.clicked.connect(self._add_video)
        media_row.addWidget(add_photo)
        media_row.addWidget(add_video)
        root.addLayout(media_row)

        root.addWidget(QLabel(tr("cx.signature_heading")))
        self._pad = _SignaturePad()
        root.addWidget(self._pad)
        sig_row = QHBoxLayout()
        clear_sig = QPushButton(tr("cx.clear_signature"))
        clear_sig.clicked.connect(self._pad.clear)
        save_sig = QPushButton(tr("cx.save_signature"))
        save_sig.setObjectName("PrimaryButton")
        save_sig.clicked.connect(self._save_signature)
        sig_row.addWidget(clear_sig)
        sig_row.addWidget(save_sig)
        root.addLayout(sig_row)

        doc_row = QHBoxLayout()
        pdf_btn = QPushButton(tr("cx.generate_pdf"))
        pdf_btn.clicked.connect(self._generate_pdf)
        warranty_btn = QPushButton(tr("cx.show_warranty"))
        warranty_btn.clicked.connect(self._show_warranty)
        doc_row.addWidget(pdf_btn)
        doc_row.addWidget(warranty_btn)
        root.addLayout(doc_row)

        self._info = QLabel("")
        self._info.setWordWrap(True)
        root.addWidget(self._info)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText(tr("common.close"))
            close_btn.clicked.connect(self.accept)
        root.addWidget(buttons)
        self._load_quote_amount()
        self._reload_media()

    def _load_quote_amount(self) -> None:
        db = self._container.create_session()
        try:
            wo = WorkOrderRepository(db).get_by_id(self._work_order_id)
            if wo is not None:
                self._quote_amount.setValue(int(wo.estimated_cost or 0))
        finally:
            db.close()

    def _submit_quote(self) -> None:
        db = self._container.create_session()
        try:
            QuoteService(db).submit_quote(
                self._work_order_id,
                estimated_cost=self._quote_amount.value(),
                actor_id=self._session.user_id,
            )
            db.commit()
            self._info.setText(tr("cx.quote_sent"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _admin_override(self) -> None:
        reason, ok = QInputDialog.getMultiLineText(
            self,
            tr("cx.admin_override"),
            tr("cx.admin_override_prompt"),
        )
        if not ok:
            return
        db = self._container.create_session()
        try:
            QuoteService(db).start_repair_with_override(
                self._work_order_id,
                reason=reason,
                actor_id=self._session.user_id,
            )
            db.commit()
            self._info.setText(tr("cx.admin_override_done"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _reload_media(self) -> None:
        db = self._container.create_session()
        try:
            items = MediaService(db).list_media(self._work_order_id)
            self._media_list.clear()
            for item in items:
                self._media_list.addItem(
                    f"{item.media_type} · {item.category} · {item.phase} · {item.file_path}"
                )
            if not items:
                self._media_list.addItem(tr("cx.media_empty"))
        finally:
            db.close()

    def _add_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("cx.add_photo"), "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        db = self._container.create_session()
        try:
            MediaService(db).add_photo(
                self._work_order_id,
                Path(path),
                actor_id=self._session.user_id,
            )
            db.commit()
            self._reload_media()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _add_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("cx.add_video"), "", "Video (*.mp4 *.mov *.avi)"
        )
        if not path:
            return
        db = self._container.create_session()
        try:
            MediaService(db).add_video(
                self._work_order_id,
                Path(path),
                actor_id=self._session.user_id,
            )
            db.commit()
            self._reload_media()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _save_signature(self) -> None:
        db = self._container.create_session()
        try:
            IntakeService(db).capture_signature(
                self._work_order_id,
                self._pad.png_bytes(),
                actor_id=self._session.user_id,
            )
            db.commit()
            self._info.setText(tr("cx.signature_saved"))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _generate_pdf(self) -> None:
        db = self._container.create_session()
        try:
            doc = IntakeService(db).generate_receipt_pdf(
                self._work_order_id, actor_id=self._session.user_id
            )
            db.commit()
            self._info.setText(tr("cx.pdf_saved", path=doc.file_path))
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
        finally:
            db.close()

    def _show_warranty(self) -> None:
        db = self._container.create_session()
        try:
            card = WarrantyService(db).get_for_work_order(self._work_order_id)
            if card is None:
                self._info.setText(tr("cx.warranty_none"))
            else:
                self._info.setText(
                    tr(
                        "cx.warranty_info",
                        number=card.warranty_number,
                        until=str(card.expires_at.date()),
                    )
                )
        finally:
            db.close()
