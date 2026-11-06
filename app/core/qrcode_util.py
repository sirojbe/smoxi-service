"""QR code helpers for deep links (Telegram bot, etc.)."""

from __future__ import annotations

import io

from PySide6.QtGui import QImage, QPixmap

from app.config.logging import get_logger

logger = get_logger("qrcode")


class QrCodeError(RuntimeError):
    """QR image could not be generated."""


def qr_png_bytes(text: str, *, box_size: int = 8, border: int = 2) -> bytes:
    """Encode *text* as PNG bytes (QR)."""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError as exc:
        raise QrCodeError(
            "QR uchun qrcode o‘rnatilmagan. pip install \"qrcode[pil]\""
        ) from exc

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)

    # Prefer pure PNG factory (no Pillow quirks); fall back to PIL.
    try:
        from qrcode.image.pure import PyPNGImage

        image = qr.make_image(image_factory=PyPNGImage)
        buffer = io.BytesIO()
        image.save(buffer)
        data = buffer.getvalue()
    except Exception:  # noqa: BLE001
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        if hasattr(image, "convert"):
            image = image.convert("RGB")
        image.save(buffer, format="PNG")
        data = buffer.getvalue()

    if not data:
        raise QrCodeError("QR PNG boʻsh.")
    return data


def qr_pixmap_from_text(text: str, *, box_size: int = 8, border: int = 2) -> QPixmap:
    """
    Render *text* (usually a URL) as a QR code pixmap for on-screen display.

    Scanning the QR with a phone camera opens the URL — for Telegram deep links
    this launches the bot with /start payload automatically.
    """
    data = qr_png_bytes(text, box_size=box_size, border=border)
    qimage = QImage.fromData(data, "PNG")
    if qimage.isNull():
        logger.error("QImage.fromData QR PNG ni o‘qimadi ({} bayt)", len(data))
        raise QrCodeError("QR rasmni yuklab boʻlmadi.")
    pixmap = QPixmap.fromImage(qimage)
    if pixmap.isNull():
        raise QrCodeError("QR pixmap boʻsh.")
    return pixmap
