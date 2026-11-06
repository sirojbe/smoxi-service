"""Device create/edit dialog."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from app.localization.translator import tr
from app.modules.customers.models.device import Device
from app.modules.customers.schemas.customer_schema import DeviceCreateSchema, DeviceUpdateSchema

DEVICE_TYPES: tuple[tuple[str, str], ...] = (
    ("phone", "customers.device_phone"),
    ("laptop", "customers.device_laptop"),
    ("tablet", "customers.device_tablet"),
    ("computer", "customers.device_computer"),
    ("tv", "customers.device_tv"),
    ("other", "customers.device_other"),
)


class DeviceFormDialog(QDialog):
    """Dialog for creating or editing a device."""

    def __init__(self, parent=None, *, device: Device | None = None) -> None:
        super().__init__(parent)
        self._device = device
        self._payload: DeviceCreateSchema | DeviceUpdateSchema | None = None
        self.setWindowTitle(
            tr("customers.device_edit") if device else tr("customers.device_new")
        )
        self.setMinimumWidth(420)
        self._build_ui()
        if device is not None:
            self._fill(device)

    @property
    def payload(self) -> DeviceCreateSchema | DeviceUpdateSchema | None:
        return self._payload

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._type = QComboBox()
        for code, key in DEVICE_TYPES:
            self._type.addItem(tr(key), code)
        self._brand = QLineEdit()
        self._model = QLineEdit()
        self._imei = QLineEdit()
        self._serial = QLineEdit()
        self._color = QLineEdit()
        self._access = QLineEdit()
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)

        form.addRow(tr("customers.device_type"), self._type)
        form.addRow(tr("customers.brand"), self._brand)
        form.addRow(tr("customers.model"), self._model)
        form.addRow(tr("customers.imei"), self._imei)
        form.addRow(tr("customers.serial"), self._serial)
        form.addRow(tr("customers.color"), self._color)
        form.addRow(tr("customers.access_code"), self._access)
        form.addRow(tr("customers.notes"), self._notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, device: Device) -> None:
        index = self._type.findData(device.device_type)
        if index >= 0:
            self._type.setCurrentIndex(index)
        self._brand.setText(device.brand or "")
        self._model.setText(device.model)
        self._imei.setText(device.imei or "")
        self._serial.setText(device.serial_number or "")
        self._color.setText(device.color or "")
        self._access.setText(device.access_code or "")
        self._notes.setPlainText(device.notes or "")

    def _on_save(self) -> None:
        data = {
            "device_type": self._type.currentData(),
            "brand": self._brand.text(),
            "model": self._model.text(),
            "imei": self._imei.text(),
            "serial_number": self._serial.text(),
            "color": self._color.text(),
            "access_code": self._access.text(),
            "notes": self._notes.toPlainText(),
        }
        try:
            if self._device is None:
                self._payload = DeviceCreateSchema.model_validate(data)
            else:
                self._payload = DeviceUpdateSchema.model_validate(data)
            self.accept()
        except PydanticValidationError as exc:
            message = exc.errors()[0].get("msg", tr("common.error"))
            QMessageBox.warning(self, tr("common.error"), str(message))
