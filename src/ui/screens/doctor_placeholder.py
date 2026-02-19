from datetime import datetime

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from src.config import get_config
from src.service.database.actions import AppointmentView, get_doctor_appointments, update_appointment_by_doctor
from src.service.database.models import AppointmentStatus, StorageStatus
from src.ui.screens.base import DarkScreen
from src.ui.screens.modal_window.modal_with_ok import show_modal

STATUS_LABELS = {
    AppointmentStatus.SCHEDULED: "Запланирован",
    AppointmentStatus.COMPLETED: "Завершён",
    AppointmentStatus.CANCELLED: "Отменён",
}
LABEL_TO_STATUS = {label: status for status, label in STATUS_LABELS.items()}


class DoctorPlaceholderScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "doctor"
        self.conf = get_config()
        self._appointments: list[AppointmentView] = []
        self._filter = "future"

        layout = BoxLayout(orientation="vertical", padding=20, spacing=12)
        top = BoxLayout(size_hint_y=None, height=44, spacing=8)
        top.add_widget(
            Button(
                text="Выйти",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                size_hint_x=0.2,
                on_press=lambda *_: self.manager.safe_switch("auth"),
            )
        )
        top.add_widget(Label(text="Кабинет врача", color=self.conf.text_color, font_size="22sp"))
        top.add_widget(
            Button(
                text="Обновить",
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                size_hint_x=0.25,
                on_press=lambda *_: self.refresh(),
            )
        )
        layout.add_widget(top)

        filters = BoxLayout(size_hint_y=None, height=42, spacing=8)
        self.filter_spinner = Spinner(
            text="Будущие приёмы",
            values=("Будущие приёмы", "Прошедшие приёмы", "Все приёмы"),
            background_color=self.conf.secondary_btn,
            color=self.conf.text_color,
        )
        self.filter_spinner.bind(text=lambda *_: self._on_filter_change())
        filters.add_widget(Label(text="Фильтр:", color=self.conf.text_color, size_hint_x=0.22))
        filters.add_widget(self.filter_spinner)
        layout.add_widget(filters)

        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        self.set_message("Загрузка приёмов...")
        self.run_async(
            get_doctor_appointments(self.manager.current_user_id),
            self._after_load,
            lambda msg: self.set_message(msg),
        )

    def _after_load(self, appointments: list[AppointmentView]):
        self._appointments = appointments
        self._render_appointments()

    def _on_filter_change(self):
        mapping = {
            "Будущие приёмы": "future",
            "Прошедшие приёмы": "past",
            "Все приёмы": "all",
        }
        self._filter = mapping.get(self.filter_spinner.text, "future")
        self._render_appointments()

    def _filtered(self) -> list[AppointmentView]:
        now = datetime.now()
        if self._filter == "all":
            return self._appointments
        if self._filter == "past":
            return [item for item in self._appointments if item.dt < now]
        return [item for item in self._appointments if item.dt >= now]

    def _render_appointments(self):
        self.list_layout.clear_widgets()
        appointments = self._filtered()

        if not appointments:
            self.list_layout.add_widget(Label(text="Приёмов нет", color=self.conf.hint_color, size_hint_y=None, height=40))
            self.set_message("Приёмы не найдены")
            return

        for appointment in appointments:
            status_label = STATUS_LABELS.get(appointment.status, appointment.status.value)
            btn = Button(
                text=(
                    f"{appointment.dt.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Пациент: {appointment.patient_fio} | Статус: {status_label}"
                ),
                size_hint_y=None,
                height=72,
                halign="left",
                valign="middle",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
            )
            btn.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width - 20, inst.height)))
            btn.bind(on_press=lambda _, a=appointment: self._open_details(a))
            self.list_layout.add_widget(btn)

        self.set_message(f"Найдено приёмов: {len(appointments)}")

    def _open_details(self, appointment: AppointmentView):
        try:
            open_appointment_modal(self, appointment, StorageStatus.DOCTOR, self.refresh)
        except Exception as exc:
            show_modal(f"Ошибка при открытии приёма: {exc}")


def open_appointment_modal(parent, appointment: AppointmentView, role: StorageStatus, on_saved=None):
    conf = get_config()
    modal = ModalView(size_hint=(0.88, 0.9), auto_dismiss=False)
    root = BoxLayout(orientation="vertical", spacing=8, padding=12)
    root.add_widget(Label(text="Данные приёма", color=conf.text_color, font_size="20sp", size_hint_y=None, height=34))
    root.add_widget(Label(text=f"Дата и время: {appointment.dt.strftime('%d.%m.%Y %H:%M')}", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(Label(text=f"Врач: {appointment.doctor_fio}", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(Label(text=f"Пациент: {appointment.patient_fio}", color=conf.text_color, size_hint_y=None, height=24))

    complaint = TextInput(text=appointment.complaint or "", hint_text="Жалобы пациента", multiline=True)
    condition = TextInput(text=appointment.condition or "", hint_text="Состояние пациента", multiline=True)
    conclusion = TextInput(text=appointment.conclusion or "", hint_text="Заключение врача", multiline=True)

    current_status_label = STATUS_LABELS.get(appointment.status, appointment.status.value)
    status = Spinner(
        text=current_status_label,
        values=tuple(STATUS_LABELS.values()),
        background_color=conf.secondary_btn,
        color=conf.text_color,
        size_hint_y=None,
        height=44,
    )

    can_edit = role == StorageStatus.DOCTOR
    complaint.disabled = not can_edit
    condition.disabled = not can_edit
    conclusion.disabled = not can_edit
    status.disabled = not can_edit

    root.add_widget(Label(text="Жалобы", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(complaint)
    root.add_widget(Label(text="Состояние", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(condition)
    root.add_widget(Label(text="Заключение", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(conclusion)
    root.add_widget(Label(text="Статус", color=conf.text_color, size_hint_y=None, height=24))
    root.add_widget(status)

    actions = BoxLayout(size_hint_y=None, height=44, spacing=8)

    if can_edit:

        def save(*_):
            selected_status = LABEL_TO_STATUS.get(status.text)
            if selected_status is None:
                show_modal("Некорректный статус")
                return

            parent.run_async(
                update_appointment_by_doctor(
                    parent.manager.current_user_id,
                    appointment.id,
                    complaint.text,
                    condition.text,
                    conclusion.text,
                    selected_status,
                ),
                lambda *_: _saved(modal, on_saved),
                lambda msg: show_modal(msg),
            )

        actions.add_widget(
            Button(
                text="Сохранить",
                on_press=save,
                background_color=conf.primary_btn,
                color=conf.text_color,
            )
        )

    actions.add_widget(
        Button(
            text="Закрыть",
            on_press=lambda *_: modal.dismiss(),
            background_color=conf.secondary_btn,
            color=conf.text_color,
        )
    )

    root.add_widget(actions)
    modal.add_widget(root)
    modal.open()


def _saved(modal: ModalView, on_saved):
    modal.dismiss()
    show_modal("Данные приёма обновлены")
    if on_saved:
        on_saved()
