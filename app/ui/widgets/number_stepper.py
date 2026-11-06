"""Modern − / value / + numeric stepper — single unified control."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)


class NumberStepper(QFrame):
    """One rounded field: [−] value [+] — no classic Windows spin arrows."""

    valueChanged = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 0,
        step: int = 1,
        suffix: str = "",
        object_name: str | None = None,
        button_size: int = 40,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("NumberStepper")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._button_size = button_size

        self._spin = QSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setValue(value)
        self._spin.setSingleStep(step)
        self._spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin.setFrame(False)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        if suffix:
            self._spin.setSuffix(suffix)
        if object_name:
            self._spin.setObjectName(object_name)
        self._spin.setFixedHeight(button_size - 2)
        self._spin.valueChanged.connect(self.valueChanged.emit)

        self._minus = QPushButton("−")
        self._minus.setObjectName("StepperMinus")
        self._minus.setFixedSize(button_size, button_size)
        self._minus.setAutoRepeat(True)
        self._minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._minus.setFlat(True)
        self._minus.clicked.connect(self._spin.stepDown)

        self._plus = QPushButton("+")
        self._plus.setObjectName("StepperPlus")
        self._plus.setFixedSize(button_size, button_size)
        self._plus.setAutoRepeat(True)
        self._plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._plus.setFlat(True)
        self._plus.clicked.connect(self._spin.stepUp)

        row = QHBoxLayout(self)
        row.setContentsMargins(1, 1, 1, 1)
        row.setSpacing(0)
        row.addWidget(self._minus)
        row.addWidget(self._spin, stretch=1)
        row.addWidget(self._plus)
        self.setFixedHeight(button_size)

    @property
    def spin(self) -> QSpinBox:
        return self._spin

    def value(self) -> int:
        return self._spin.value()

    def setValue(self, value: int) -> None:
        self._spin.setValue(value)

    def setRange(self, minimum: int, maximum: int) -> None:
        self._spin.setRange(minimum, maximum)

    def setSingleStep(self, step: int) -> None:
        self._spin.setSingleStep(step)

    def setSuffix(self, suffix: str) -> None:
        self._spin.setSuffix(suffix)

    def setGroupSeparatorShown(self, shown: bool) -> None:
        self._spin.setGroupSeparatorShown(shown)

    def setMinimumHeight(self, height: int) -> None:  # noqa: N802 — Qt API
        self._apply_size(height)

    def setFixedHeight(self, height: int) -> None:  # noqa: N802 — Qt API
        self._apply_size(height)

    def _apply_size(self, height: int) -> None:
        self._button_size = height
        self._spin.setFixedHeight(max(height - 2, 24))
        self._minus.setFixedSize(height, height)
        self._plus.setFixedSize(height, height)
        super().setFixedHeight(height)

    def blockSignals(self, block: bool) -> bool:  # noqa: N802 — Qt API
        self._spin.blockSignals(block)
        return super().blockSignals(block)
