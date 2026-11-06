"""Dialog showing Telegram bot deep-link as a scannable QR code."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.logging import get_logger
from app.core.qrcode_util import QrCodeError, qr_pixmap_from_text
from app.localization.translator import tr

logger = get_logger("reception.qr")


class BotLinkQrDialog(QDialog):
    """Show QR for t.me bot link — phone scan opens Telegram automatically."""

    def __init__(
        self,
        parent: QWidget,
        *,
        bot_link: str,
        work_order_number: str,
    ) -> None:
        super().__init__(parent)
        self._bot_link = bot_link
        self.setWindowTitle(tr("reception.qr_title"))
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(
            tr("reception.qr_heading", number=work_order_number),
            objectName="PageTitle",
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        hint = QLabel(tr("reception.qr_hint"))
        hint.setWordWrap(True)
        hint.setObjectName("HintLabel")
        layout.addWidget(hint)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setMinimumSize(300, 300)
        try:
            pixmap = qr_pixmap_from_text(bot_link, box_size=10, border=2)
            qr_label.setPixmap(
                pixmap.scaled(
                    300,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("QR yaratilmadi: {}", exc)
            message = (
                tr("reception.qr_failed")
                if not isinstance(exc, QrCodeError)
                else str(exc)
            )
            qr_label.setText(message)
            qr_label.setWordWrap(True)
            qr_label.setStyleSheet("color: #8A3B32; font-weight: 600;")
        layout.addWidget(qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        link_row = QLabel(bot_link)
        link_row.setWordWrap(True)
        link_row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        link_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_row.setObjectName("MutedLabel")
        layout.addWidget(link_row)

        actions = QHBoxLayout()
        copy_btn = QPushButton(tr("reception.copy_link"))
        copy_btn.clicked.connect(self._copy)
        open_btn = QPushButton(tr("reception.open_link"))
        open_btn.clicked.connect(self._open)
        actions.addWidget(copy_btn)
        actions.addWidget(open_btn)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr("common.close"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._bot_link)
        QMessageBox.information(self, tr("reception.qr_title"), tr("reception.link_copied"))

    def _open(self) -> None:
        QDesktopServices.openUrl(QUrl(self._bot_link))
