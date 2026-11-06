"""About page — product, version, license summary."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from app.config.settings import get_settings
from app.localization.translator import tr
from app.plugins.registry import plugin_registry


class AboutPage(QWidget):
    """Product identity and third-party / plugin notices."""

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("about.title"), objectName="PageTitle"))
        root.addWidget(
            QLabel(tr("about.product", name=settings.app_name, version=settings.app_version))
        )
        root.addWidget(QLabel(tr("about.subtitle")))

        self._body = QTextBrowser()
        plugins = "".join(
            f"<li><b>{p.name}</b> {p.version} — {p.description}</li>"
            for p in plugin_registry.list_plugins()
        )
        self._body.setHtml(
            f"<p>{tr('about.license')}</p>"
            f"<p>{tr('about.third_party')}</p>"
            f"<h3>{tr('about.plugins')}</h3><ul>{plugins}</ul>"
            f"<p>{tr('about.copyright')}</p>"
        )
        root.addWidget(self._body, stretch=1)

        update_btn = QPushButton(tr("about.check_update"))
        update_btn.clicked.connect(self._check_update)
        root.addWidget(update_btn)
        self._update_info = QLabel(tr("about.update_manual"))
        self._update_info.setWordWrap(True)
        root.addWidget(self._update_info)

    def _check_update(self) -> None:
        self._update_info.setText(tr("about.update_ok", version=get_settings().app_version))
