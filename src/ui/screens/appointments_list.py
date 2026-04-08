from typing import Optional

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from src.config import get_config
from src.service.database.actions import (
    AppointmentView,
    get_appointments_by_doctor_id,
    get_doctor_appointments,
    get_patient_appointments,
    update_appointment_by_doctor,
)
from src.service.database.models import AppointmentStatus, StorageStatus
from src.ui.screens.base import DarkScreen
from src.ui.screens.modal_window.modal_with_ok import show_modal

STATUS_LABELS = {
    AppointmentStatus.SCHEDULED: "Запланирован",
    AppointmentStatus.COMPLETED: "Завершён",
    AppointmentStatus.CANCELLED: "Отменён",
}
LABEL_TO_STATUS = {label: status for status, label in STATUS_LABELS.items()}


class AppointmentListScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "appointments"
        self.conf = get_config()
        self._appointments: list[AppointmentView] = []
        self._filter = "future"
        self._context_role = StorageStatus.DOCTOR
        self._context_doctor_id: Optional[int] = None
        self._context_caption = "Мои приёмы"

        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

        self.back_btn = Button(
            text="Выйти",
            size_hint_x=0.2,
            background_color=self.conf.secondary_btn,
            color=self.conf.text_color,
            on_press=self._on_back,
        )
        self.title_label = Label(
            text=self._context_caption,
            color=self.conf.text_color,
            font_size=sp(22),
            bold=True,
            halign="center",
            valign="middle",
        )
        self.refresh_btn = Button(
            text="Обновить",
            size_hint_x=0.25,
            background_color=self.conf.primary_btn,
            color=self.conf.text_color,
            on_press=lambda *_: self.refresh(),
        )

        top.add_widget(self.back_btn)
        top.add_widget(self.title_label)
        top.add_widget(self.refresh_btn)
        layout.add_widget(top)

        filters = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
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
        self.list_layout = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def set_context(self, role: StorageStatus, doctor_id: Optional[int] = None, doctor_name: Optional[str] = None):
        self._context_role = role
        self._context_doctor_id = doctor_id
        if role == StorageStatus.ADMIN:
            self._context_caption = f"Записи врача: {doctor_name or '...'}"
        else:
            self._context_caption = "Мои приёмы"
        self.title_label.text = self._context_caption
        self._filter = "future"
        self.filter_spinner.text = "Будущие приёмы"
        self._update_back_text()

    def on_pre_enter(self, *_):
        self.refresh()

    def _update_back_text(self):
        if self._context_role == StorageStatus.ADMIN:
            self.back_btn.text = "Назад"
        elif self._context_role == StorageStatus.PATIENT:
            self.back_btn.text = "Назад"
        else:
            self.back_btn.text = "Выйти"

    def _on_back(self, *_):
        if self._context_role == StorageStatus.ADMIN:
            self.manager.safe_switch("admin")
        elif self._context_role == StorageStatus.PATIENT:
            self.manager.safe_switch("patient")
        else:
            self.manager.safe_switch("auth")

    def _on_filter_change(self):
        mapping = {
            "Будущие приёмы": "future",
            "Прошедшие приёмы": "past",
            "Все приёмы": "all",
        }
        self._filter = mapping.get(self.filter_spinner.text, "future")
        self._render_appointments()

    def refresh(self):
        if self._context_role == StorageStatus.ADMIN and self._context_doctor_id is None:
            self.set_message("Доктор не выбран")
            return

        self.set_message("Загрузка приёмов...")
        coro = self._load_appointments()
        self.run_async(coro, self._after_load, lambda msg: self.set_message(msg))

    async def _load_appointments(self):
        if self._context_role == StorageStatus.DOCTOR:
            return await get_doctor_appointments(self.manager.current_user_id)
        if self._context_role == StorageStatus.PATIENT:
            return await get_patient_appointments(self.manager.current_user_id)
        return await get_appointments_by_doctor_id(self._context_doctor_id)

    def _after_load(self, appointments: list[AppointmentView]):
        self._appointments = appointments
        self._render_appointments()

    def _filtered(self) -> list[AppointmentView]:
        if self._filter == "all":
            return self._appointments
        if self._filter == "past":
            return [
                item for item in self._appointments
                if item.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED)
            ]
        return [item for item in self._appointments if item.status == AppointmentStatus.SCHEDULED]

    def _render_appointments(self):
        self.list_layout.clear_widgets()
        appointments = self._filtered()

        if not appointments:
            self.list_layout.add_widget(Label(
                text="Приёмов нет",
                color=self.conf.hint_color,
                size_hint_y=None,
                height=dp(40),
            ))
            self.set_message("Приёмы не найдены")
            return

        can_edit = self._context_role == StorageStatus.DOCTOR
        for appointment in appointments:
            status_label = STATUS_LABELS.get(appointment.status, appointment.status.value)
            btn = Button(
                text=(
                    f"{appointment.dt.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Пациент: {appointment.patient_fio} | Статус: {status_label}"
                ),
                size_hint_y=None,
                height=dp(72),
                halign="left",
                valign="middle",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
            )
            btn.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width - dp(20), inst.height)))
            btn.bind(on_press=lambda _, a=appointment: self._open_details(a, can_edit))
            self.list_layout.add_widget(btn)

        self.set_message(f"Найдено приёмов: {len(appointments)}")

    def _open_details(self, appointment: AppointmentView, can_edit: bool):
        open_appointment_modal(
            parent=self,
            appointment=appointment,
            role=StorageStatus.DOCTOR if can_edit else StorageStatus.PATIENT,
            on_saved=self.refresh if can_edit else None,
        )


def open_appointment_modal(parent, appointment: AppointmentView, role: StorageStatus, on_saved=None):
    conf = get_config()
    modal = ModalView(size_hint=(0.88, 0.9), auto_dismiss=False)
    root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
    root.add_widget(Label(
        text="Данные приёма",
        color=conf.text_color,
        font_size=sp(20),
        size_hint_y=None,
        height=dp(34),
    ))
    root.add_widget(Label(
        text=f"Дата и время: {appointment.dt.strftime('%d.%m.%Y %H:%M')}",
        color=conf.text_color,
        size_hint_y=None,
        height=dp(24),
    ))
    root.add_widget(Label(
        text=f"Врач: {appointment.doctor_fio}",
        color=conf.text_color,
        size_hint_y=None,
        height=dp(24),
    ))
    root.add_widget(Label(
        text=f"Пациент: {appointment.patient_fio}",
        color=conf.text_color,
        size_hint_y=None,
        height=dp(24),
    ))

    complaint = TextInput(text=appointment.complaint, hint_text="Жалобы пациента", multiline=True)
    condition = TextInput(text=appointment.condition, hint_text="Состояние пациента", multiline=True)
    conclusion = TextInput(text=appointment.conclusion, hint_text="Заключение врача", multiline=True)

    current_status_label = STATUS_LABELS.get(appointment.status, appointment.status.value)
    status = Spinner(
        text=current_status_label,
        values=tuple(STATUS_LABELS.values()),
        background_color=conf.secondary_btn,
        color=conf.text_color,
        size_hint_y=None,
        height=dp(44),
    )

    can_edit = role == StorageStatus.DOCTOR
    complaint.disabled = not can_edit
    condition.disabled = not can_edit
    conclusion.disabled = not can_edit
    status.disabled = not can_edit

    root.add_widget(Label(text="Жалобы", color=conf.text_color, size_hint_y=None, height=dp(24)))
    root.add_widget(complaint)
    root.add_widget(Label(text="Состояние", color=conf.text_color, size_hint_y=None, height=dp(24)))
    root.add_widget(condition)
    root.add_widget(Label(text="Заключение", color=conf.text_color, size_hint_y=None, height=dp(24)))
    root.add_widget(conclusion)
    root.add_widget(Label(text="Статус", color=conf.text_color, size_hint_y=None, height=dp(24)))
    root.add_widget(status)

    actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

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
