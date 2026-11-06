"""Calendar page — Month / Week / Day / Agenda views."""

from __future__ import annotations

from calendar import monthcalendar
from datetime import UTC, date, datetime, time, timedelta

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.container import ServiceContainer
from app.core.exceptions import AppError
from app.core.session import DesktopSession
from app.localization.translator import tr
from app.modules.calendar.models.event import (
    EVENT_APPOINTMENT,
    EVENT_REMINDER,
    EVENT_SHIFT,
    EVENT_WORK_ORDER,
    CalendarEvent,
)
from app.modules.calendar.schemas.event_schema import (
    CalendarEventCreateSchema,
    CalendarEventUpdateSchema,
)
from app.modules.calendar.services.calendar_service import CalendarService
from app.modules.technicians.services.technician_service import TechnicianService


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _type_label(code: str) -> str:
    return {
        EVENT_APPOINTMENT: tr("calendar.type_appointment"),
        EVENT_SHIFT: tr("calendar.type_shift"),
        EVENT_REMINDER: tr("calendar.type_reminder"),
        EVENT_WORK_ORDER: tr("calendar.type_work_order"),
    }.get(code, code)


class EventFormDialog(QDialog):
    """Create / edit calendar event."""

    def __init__(
        self,
        parent: QWidget,
        *,
        technicians: list[tuple[int, str]],
        event: CalendarEvent | None = None,
        default_day: date | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            tr("calendar.edit_title") if event else tr("calendar.new_title")
        )
        self.setMinimumWidth(420)
        self.payload: CalendarEventCreateSchema | None = None
        form = QFormLayout(self)

        self._title = QLineEdit(event.title if event else "")
        self._type = QComboBox()
        for code in (
            EVENT_APPOINTMENT,
            EVENT_SHIFT,
            EVENT_REMINDER,
            EVENT_WORK_ORDER,
        ):
            self._type.addItem(_type_label(code), code)
        if event:
            idx = self._type.findData(event.event_type)
            if idx >= 0:
                self._type.setCurrentIndex(idx)

        day = (
            event.starts_at.date()
            if event
            else (default_day or date.today())
        )
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("dd.MM.yyyy")
        self._date.setDate(QDate(day.year, day.month, day.day))

        start_t = event.starts_at.time() if event else time(9, 0)
        end_t = event.ends_at.time() if event else time(10, 0)
        self._start = QTimeEdit()
        self._start.setDisplayFormat("HH:mm")
        self._start.setTime(QTime(start_t.hour, start_t.minute))
        self._end = QTimeEdit()
        self._end.setDisplayFormat("HH:mm")
        self._end.setTime(QTime(end_t.hour, end_t.minute))

        self._tech = QComboBox()
        self._tech.addItem(tr("calendar.no_technician"), None)
        for tid, name in technicians:
            self._tech.addItem(name, tid)
        if event and event.technician_id:
            idx = self._tech.findData(event.technician_id)
            if idx >= 0:
                self._tech.setCurrentIndex(idx)

        self._wo = QSpinBox()
        self._wo.setRange(0, 10_000_000)
        self._wo.setSpecialValueText("—")
        self._wo.setValue(event.work_order_id or 0 if event else 0)

        self._location = QLineEdit(event.location or "" if event else "")
        self._desc = QTextEdit()
        self._desc.setPlainText(event.description or "" if event else "")
        self._desc.setMaximumHeight(80)

        form.addRow(tr("calendar.title_field"), self._title)
        form.addRow(tr("calendar.type"), self._type)
        form.addRow(tr("calendar.date"), self._date)
        form.addRow(tr("calendar.start"), self._start)
        form.addRow(tr("calendar.end"), self._end)
        form.addRow(tr("calendar.technician"), self._tech)
        form.addRow(tr("calendar.work_order_id"), self._wo)
        form.addRow(tr("calendar.location"), self._location)
        form.addRow(tr("calendar.description"), self._desc)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText(tr("common.save"))
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText(tr("common.cancel"))
        form.addRow(buttons)

    def _accept(self) -> None:
        qd = self._date.date()
        day = date(qd.year(), qd.month(), qd.day())
        st = self._start.time()
        et = self._end.time()
        starts = _utc(
            datetime(day.year, day.month, day.day, st.hour(), st.minute(), tzinfo=UTC)
        )
        ends = _utc(
            datetime(day.year, day.month, day.day, et.hour(), et.minute(), tzinfo=UTC)
        )
        wo = self._wo.value() or None
        try:
            self.payload = CalendarEventCreateSchema(
                title=self._title.text(),
                description=self._desc.toPlainText() or None,
                event_type=str(self._type.currentData()),
                starts_at=starts,
                ends_at=ends,
                technician_id=self._tech.currentData(),
                work_order_id=wo,
                location=self._location.text() or None,
            )
        except Exception as exc:  # noqa: BLE001 — pydantic
            QMessageBox.warning(self, tr("common.error"), str(exc))
            return
        self.accept()


class CalendarPage(QWidget):
    """Scheduling calendar for appointments, shifts, reminders."""

    def __init__(self, container: ServiceContainer, session: DesktopSession) -> None:
        super().__init__()
        self._container = container
        self._session = session
        self._month_cursor = date.today().replace(day=1)
        self._selected_day = date.today()
        self._build_ui()
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        root.addWidget(QLabel(tr("calendar.title"), objectName="PageTitle"))
        root.addWidget(QLabel(tr("calendar.subtitle")))

        toolbar = QHBoxLayout()
        self._period_label = QLabel()
        prev_btn = QPushButton("◀")
        prev_btn.clicked.connect(self._prev_month)
        next_btn = QPushButton("▶")
        next_btn.clicked.connect(self._next_month)
        today_btn = QPushButton(tr("calendar.today"))
        today_btn.clicked.connect(self._go_today)
        add_btn = QPushButton(tr("calendar.add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(lambda: self._open_form())
        edit_btn = QPushButton(tr("calendar.edit"))
        edit_btn.clicked.connect(self._edit_selected)
        del_btn = QPushButton(tr("calendar.delete"))
        del_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(prev_btn)
        toolbar.addWidget(self._period_label)
        toolbar.addWidget(next_btn)
        toolbar.addWidget(today_btn)
        toolbar.addStretch()
        toolbar.addWidget(add_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(del_btn)
        root.addLayout(toolbar)

        self._tabs = QTabWidget()
        self._month_table = QTableWidget(6, 7)
        self._month_table.setHorizontalHeaderLabels(
            [
                tr("calendar.mon"),
                tr("calendar.tue"),
                tr("calendar.wed"),
                tr("calendar.thu"),
                tr("calendar.fri"),
                tr("calendar.sat"),
                tr("calendar.sun"),
            ]
        )
        self._month_table.verticalHeader().setVisible(False)
        self._month_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._month_table.cellClicked.connect(self._on_month_cell)
        self._month_table.horizontalHeader().setStretchLastSection(True)
        self._tabs.addTab(self._month_table, tr("calendar.view_month"))

        self._week_list = QListWidget()
        self._week_list.itemDoubleClicked.connect(lambda _i: self._edit_selected())
        self._tabs.addTab(self._week_list, tr("calendar.view_week"))

        self._day_list = QListWidget()
        self._day_list.itemDoubleClicked.connect(lambda _i: self._edit_selected())
        self._tabs.addTab(self._day_list, tr("calendar.view_day"))

        self._agenda = QListWidget()
        self._agenda.itemDoubleClicked.connect(lambda _i: self._edit_selected())
        self._tabs.addTab(self._agenda, tr("calendar.view_agenda"))
        self._tabs.currentChanged.connect(lambda _i: self.refresh())
        root.addWidget(self._tabs, stretch=1)

        self._hint = QLabel(tr("calendar.hint"))
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

    def _technicians(self) -> list[tuple[int, str]]:
        db = self._container.create_session()
        try:
            rows = TechnicianService(db).list_technicians(self._session.user.company_id)
            return [(t.id, t.full_name) for t in rows]
        except AppError:
            return []
        finally:
            db.close()

    def _prev_month(self) -> None:
        y, m = self._month_cursor.year, self._month_cursor.month
        if m == 1:
            self._month_cursor = date(y - 1, 12, 1)
        else:
            self._month_cursor = date(y, m - 1, 1)
        self.refresh()

    def _next_month(self) -> None:
        y, m = self._month_cursor.year, self._month_cursor.month
        if m == 12:
            self._month_cursor = date(y + 1, 1, 1)
        else:
            self._month_cursor = date(y, m + 1, 1)
        self.refresh()

    def _go_today(self) -> None:
        today = date.today()
        self._month_cursor = today.replace(day=1)
        self._selected_day = today
        self.refresh()

    def _range_for_month(self) -> tuple[datetime, datetime]:
        y, m = self._month_cursor.year, self._month_cursor.month
        start = datetime(y, m, 1, tzinfo=UTC)
        if m == 12:
            end = datetime(y + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(y, m + 1, 1, tzinfo=UTC)
        return start, end

    def refresh(self) -> None:
        self._period_label.setText(
            tr(
                "calendar.period",
                month=self._month_cursor.month,
                year=self._month_cursor.year,
            )
        )
        start, end = self._range_for_month()
        week_start = self._selected_day - timedelta(days=self._selected_day.weekday())
        week_end = week_start + timedelta(days=7)
        day_start = datetime.combine(self._selected_day, time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        db = self._container.create_session()
        try:
            service = CalendarService(db)
            month_events = service.list_range(
                self._session.user.company_id, range_start=start, range_end=end
            )
            week_events = service.list_range(
                self._session.user.company_id,
                range_start=datetime.combine(week_start, time.min, tzinfo=UTC),
                range_end=datetime.combine(week_end, time.min, tzinfo=UTC),
            )
            day_events = service.list_range(
                self._session.user.company_id,
                range_start=day_start,
                range_end=day_end,
            )
            agenda = service.list_agenda(self._session.user.company_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()

        self._fill_month(month_events)
        self._fill_list(self._week_list, week_events)
        self._fill_list(self._day_list, day_events)
        self._fill_list(self._agenda, agenda)
        self._hint.setText(
            tr(
                "calendar.selected_day",
                day=self._selected_day.strftime("%d.%m.%Y"),
            )
        )

    def _fill_month(self, events: list[CalendarEvent]) -> None:
        by_day: dict[int, list[CalendarEvent]] = {}
        for ev in events:
            d = ev.starts_at.astimezone(UTC).day
            by_day.setdefault(d, []).append(ev)
        weeks = monthcalendar(self._month_cursor.year, self._month_cursor.month)
        self._month_table.setRowCount(len(weeks))
        for r, week in enumerate(weeks):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    item = QTableWidgetItem("")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                else:
                    lines = [str(day_num)]
                    for ev in by_day.get(day_num, [])[:3]:
                        lines.append(f"• {ev.title[:18]}")
                    if len(by_day.get(day_num, [])) > 3:
                        lines.append("…")
                    item = QTableWidgetItem("\n".join(lines))
                    item.setData(Qt.ItemDataRole.UserRole, day_num)
                    if date(
                        self._month_cursor.year, self._month_cursor.month, day_num
                    ) == self._selected_day:
                        item.setBackground(Qt.GlobalColor.cyan)
                self._month_table.setItem(r, c, item)
            self._month_table.setRowHeight(r, 72)

    def _fill_list(self, widget: QListWidget, events: list[CalendarEvent]) -> None:
        widget.clear()
        if not events:
            widget.addItem(tr("calendar.empty"))
            return
        for ev in events:
            stamp = ev.starts_at.astimezone(UTC).strftime("%d.%m.%Y %H:%M")
            text = (
                f"{stamp}  ·  {_type_label(ev.event_type)}\n"
                f"{ev.title}"
                + (f"  ({ev.location})" if ev.location else "")
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ev.id)
            widget.addItem(item)

    def _on_month_cell(self, row: int, col: int) -> None:
        item = self._month_table.item(row, col)
        if item is None:
            return
        day_num = item.data(Qt.ItemDataRole.UserRole)
        if not day_num:
            return
        self._selected_day = date(
            self._month_cursor.year, self._month_cursor.month, int(day_num)
        )
        self.refresh()

    def _selected_event_id(self) -> int | None:
        tab = self._tabs.currentWidget()
        if isinstance(tab, QListWidget):
            item = tab.currentItem()
            if item is None:
                return None
            data = item.data(Qt.ItemDataRole.UserRole)
            return int(data) if data else None
        return None

    def _open_form(self, event: CalendarEvent | None = None) -> None:
        dialog = EventFormDialog(
            self,
            technicians=self._technicians(),
            event=event,
            default_day=self._selected_day,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.payload is None:
            return
        db = self._container.create_session()
        try:
            service = CalendarService(db)
            if event is None:
                service.create_event(
                    self._session.user.company_id,
                    dialog.payload,
                    actor_id=self._session.user_id,
                )
            else:
                service.update_event(
                    event.id,
                    CalendarEventUpdateSchema(**dialog.payload.model_dump()),
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

    def _edit_selected(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(
                self, tr("calendar.title"), tr("calendar.select_first")
            )
            return
        db = self._container.create_session()
        try:
            event = CalendarService(db).get_event(event_id)
        except AppError as exc:
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self._open_form(event)

    def _delete_selected(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(
                self, tr("calendar.title"), tr("calendar.select_first")
            )
            return
        answer = QMessageBox.question(
            self, tr("calendar.title"), tr("calendar.delete_confirm")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db = self._container.create_session()
        try:
            CalendarService(db).soft_delete(
                event_id, actor_id=self._session.user_id
            )
            db.commit()
        except AppError as exc:
            db.rollback()
            QMessageBox.warning(self, tr("common.error"), exc.message)
            return
        finally:
            db.close()
        self.refresh()
