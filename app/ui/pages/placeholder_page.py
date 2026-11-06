"""Placeholder page for modules under development."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.localization.translator import tr


class PlaceholderPage(QWidget):
    """Simple placeholder until a module is implemented."""

    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        heading = QLabel(title, objectName="PageTitle")
        subtitle = QLabel(tr("dashboard.placeholder"))
        subtitle.setStyleSheet("color: #5B6B7C;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addStretch()
