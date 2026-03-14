from datetime import date, datetime, time, timedelta
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from src.config import get_config
from src.service.database.actions import (
    AppointmentView,
    DoctorView,
    create_appointment,
    create_doctor,
    delete_doctor,
    get_appointments_by_doctor_id,
    get_doctors,
    get_patient_appointments,
    update_doctor,
)
from src.service.database.models import AppointmentStatus, StorageStatus
from src.ui.screens.base import DarkScreen
from src.ui.screens.modal_window.modal_with_ok import show_modal
from src.ui.screens.modal_window.modal_yes_or_no import show_confirm_modal

STATUS_LABELS = {
    AppointmentStatus.SCHEDULED: "Запланирован",
    AppointmentStatus.COMPLETED: "Завершён",
    AppointmentStatus.CANCELLED: "Отменён",
}


class DoctorDirectoryScreen(DarkScreen):
    def __init__(self, role: StorageStatus, **kwargs):
        super().__init__(**kwargs)
        self.conf = get_config()
        self.role = role
        self._doctors: list[DoctorView] = []
        self.selected_doctor_id: int | None = None
        self._doctor_buttons: dict[int, Button] = {}
        self._card_default_color = self.conf.secondary_btn
        self._card_selected_color = (0.45, 0.45, 0.55, 1)

        self.name = "admin" if self.role == StorageStatus.ADMIN else "patient"
        title = "Панель администратора" if self.role == StorageStatus.ADMIN else "Кабинет пациента"

        anchor = AnchorLayout(anchor_x="center", anchor_y="top", padding=16)
        self.add_widget(anchor)

        container = BoxLayout(orientation="vertical", spacing=12, padding=16, size_hint=(0.95, 0.96))
        anchor.add_widget(container)

        # ===== Top bar =====
        top_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=8)
        self.logout_btn = Button(
            text="Выйти",
            size_hint=(None, 1),
            width=100,
            background_color=self.conf.secondary_btn,
            color=self.conf.text_color,
            on_press=lambda *_: self.manager.safe_switch("auth"),
        )
        self.refresh_btn = Button(
            text="Обновить",
            size_hint=(None, 1),
            width=110,
            background_color=self.conf.primary_btn,
            color=self.conf.text_color,
            on_press=lambda *_: self.refresh(),
        )
        self.title_label = Label(
            text=title,
            font_size="18sp",
            bold=True,
            color=self.conf.text_color,
            size_hint_x=1,
            halign="center",
            valign="middle",
            text_size=(None, 36),
            shorten=True,
            shorten_from="right"
        )
        top_bar.add_widget(self.logout_btn)
        top_bar.add_widget(self.title_label)
        top_bar.add_widget(self.refresh_btn)
        container.add_widget(top_bar)

        # ===== Filter row =====
        filter_row = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=44)
        filter_row.add_widget(
            Label(
                text="Специализация:",
                color=self.conf.text_color,
                size_hint_x=0.35,
                halign="left",
                valign="middle",
            )
        )
        self.specialization_filter = Spinner(
            text="Все специализации",
            values=("Все специализации",),
            size_hint_x=0.65,
            background_color=self.conf.secondary_btn,
            color=self.conf.text_color,
        )
        self.specialization_filter.bind(text=lambda *_: self._sync_doctor_filter())
        filter_row.add_widget(self.specialization_filter)
        container.add_widget(filter_row)

        # ===== Doctors scroll =====
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.doctors_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.doctors_layout.bind(minimum_height=self.doctors_layout.setter("height"))
        scroll.add_widget(self.doctors_layout)
        container.add_widget(scroll)

        # ===== Action buttons row с прокруткой =====
        self.action_scroll = ScrollView(size_hint=(1, None), height=44, do_scroll_y=False)
        self.action_row = BoxLayout(orientation="horizontal", spacing=8, size_hint=(None, 1))
        self.action_row.bind(minimum_width=self.action_row.setter("width"))
        self.action_scroll.add_widget(self.action_row)
        container.add_widget(self.action_scroll)
        self._build_action_buttons()

    def on_pre_enter(self, *_):
        self.refresh()

    def _build_action_buttons(self):
        self.action_row.clear_widgets()
        if self.role == StorageStatus.ADMIN:
            self.btn_add = Button(
                text="Добавить врача",
                size_hint=(None, 1),
                width=140,
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                on_press=lambda *_: self._open_doctor_form(),
            )
            self.btn_edit = Button(
                text="Изменить врача",
                size_hint=(None, 1),
                width=140,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._open_doctor_form(self._selected_doctor()),
            )
            self.btn_delete = Button(
                text="Удалить врача",
                size_hint=(None, 1),
                width=140,
                background_color=(0.7, 0.2, 0.2, 1),
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._confirm_delete(),
            )
            self.btn_appointments = Button(
                text="Записи врача",
                size_hint=(None, 1),
                width=180,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._open_admin_doctor_appointments(),
            )
            for btn in [self.btn_add, self.btn_edit, self.btn_delete, self.btn_appointments]:
                self.action_row.add_widget(btn)
        else:
            self.btn_book = Button(
                text="Записаться на приём",
                size_hint=(None, 1),
                width=160,
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._open_book_modal(),
            )
            self.btn_my_appointments = Button(
                text="Все мои записи на приём",
                size_hint=(None, 1),
                width=180,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                disabled=False,
                on_press=lambda *_: self._open_patient_appointments(),
            )
            self.action_row.add_widget(self.btn_book)
            self.action_row.add_widget(self.btn_my_appointments)

    # ===== Остальной код остаётся без изменений =====
    # методы refresh, _after_load, _load_error, _render_doctors, _select_doctor, _update_action_buttons_state и т.д.

    def refresh(self):
        self.selected_doctor_id = None
        self._doctor_buttons = {}
        self._update_action_buttons_state()
        self.set_message("Загрузка списка врачей...")
        self.run_async(get_doctors(), self._after_load, self._load_error)

    def _after_load(self, doctors: list[DoctorView]):
        self._doctors = doctors
        unique_specs = sorted({doctor.specialization for doctor in doctors})
        self.specialization_filter.values = tuple(["Все специализации", *unique_specs])
        self.specialization_filter.text = "Все специализации"
        self._render_doctors()
        self.set_message(f"Найдено врачей: {len(doctors)}")

    def _load_error(self, error_msg: str):
        self.set_message(error_msg)

    def _sync_doctor_filter(self):
        self._render_doctors()

    def _filter_by_specialization(self, doctors: list[DoctorView]) -> list[DoctorView]:
        spec = self.specialization_filter.text
        if spec == "Все специализации":
            return doctors
        return [doctor for doctor in doctors if doctor.specialization == spec]

    def _selected_doctor(self) -> DoctorView | None:
        for doctor in self._doctors:
            if doctor.id == self.selected_doctor_id:
                return doctor
        return None

    def _render_doctors(self):
        self.doctors_layout.clear_widgets()
        self._doctor_buttons = {}
        self.selected_doctor_id = None
        doctors = self._filter_by_specialization(self._doctors)

        if not doctors:
            self.doctors_layout.add_widget(
                Label(text="Врачи не найдены", color=self.conf.hint_color, size_hint_y=None, height=40)
            )
            self._update_action_buttons_state()
            return

        for doctor in doctors:
            card = BoxLayout(orientation="vertical", spacing=4, padding=10, size_hint_y=None, height=92)
            select_btn = Button(
                text=f"ФИО: {doctor.fio}\nСпециализация: {doctor.specialization}",
                halign="left",
                valign="middle",
                background_color=self._card_default_color,
                color=self.conf.text_color,
                on_press=lambda _, d_id=doctor.id: self._select_doctor(d_id),
            )
            select_btn.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width - 20, inst.height)))
            card.add_widget(select_btn)
            self.doctors_layout.add_widget(card)
            self._doctor_buttons[doctor.id] = select_btn

        self._update_action_buttons_state()

    def _select_doctor(self, doctor_id: int):
        self.selected_doctor_id = doctor_id
        self._refresh_button_colors()
        self._update_action_buttons_state()
        selected = self._selected_doctor()
        if selected:
            self.set_message(f"Выбран врач: {selected.fio}")

    def _refresh_button_colors(self):
        for d_id, button in self._doctor_buttons.items():
            if d_id == self.selected_doctor_id:
                button.background_color = self._card_selected_color
            else:
                button.background_color = self._card_default_color

    def _update_action_buttons_state(self):
        selected = self.selected_doctor_id is not None
        if self.role == StorageStatus.ADMIN:
            self.btn_edit.disabled = not selected
            self.btn_delete.disabled = not selected
            self.btn_appointments.disabled = not selected
        else:
            self.btn_book.disabled = not selected
            self.btn_my_appointments.disabled = False

    def _open_book_modal(self):
        doctor = self._selected_doctor()
        if doctor is None:
            show_modal("Выберите врача")
            return

        self.run_async(
            get_appointments_by_doctor_id(doctor.id),
            lambda appointments: self._show_book_modal(doctor, appointments),
            lambda msg: show_modal(msg),
        )

    def _show_book_modal(self, doctor: DoctorView, appointments: list[AppointmentView]):
        modal = ModalView(size_hint=(0.82, 0.76), auto_dismiss=False)
        root = BoxLayout(orientation="vertical", padding=16, spacing=10)
        root.add_widget(Label(text=f"Запись к врачу: {doctor.fio}", color=self.conf.text_color, size_hint_y=None, height=32))
        selected_date = {"value": datetime.now().date()}
        selected_dt = {"value": None}

        selected_label = Label(
            text="Выберите время приёма",
            color=self.conf.text_color,
            size_hint_y=None,
            height=28,
        )

        root.add_widget(selected_label)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        slots_grid = GridLayout(cols=3, spacing=8, padding=4, size_hint_y=None)
        slots_grid.bind(minimum_height=slots_grid.setter("height"))
        scroll.add_widget(slots_grid)
        root.add_widget(scroll)

        day_row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=44)
        day_label = Label(color=self.conf.text_color)

        def fmt_time(value: datetime) -> str:
            return value.strftime("%H:%M").lstrip("0")

        def build_day_slots(day_value: date) -> list[datetime]:
            day_start = datetime.combine(day_value, time(hour=7, minute=0))
            day_end = datetime.combine(day_value, time(hour=16, minute=0))
            slots: list[datetime] = []
            current = day_start
            while current <= day_end:
                slots.append(current)
                current += timedelta(minutes=30)
            return slots

        def refresh_slots():
            slots_grid.clear_widgets()
            day_value = selected_date["value"]
            occupied_slots = {
                appointment.dt
                for appointment in appointments
                if appointment.dt.date() == day_value
            }
            day_label.text = day_value.strftime("%d.%m.%Y")

            if selected_dt["value"] is not None and selected_dt["value"].date() != day_value:
                selected_dt["value"] = None
                selected_label.text = "Выберите время приёма"

            for slot in build_day_slots(day_value):
                is_occupied = slot in occupied_slots

                def choose_slot(_, dt=slot):
                    selected_dt["value"] = dt
                    selected_label.text = f"Выбрано: {dt.strftime('%d.%m.%Y')} {fmt_time(dt)}"

                slot_btn = Button(
                    text=fmt_time(slot),
                    size_hint_y=None,
                    height=56,
                    disabled=is_occupied,
                    background_color=(0.55, 0.2, 0.2, 1) if is_occupied else self.conf.secondary_btn,
                    color=self.conf.text_color,
                    on_press=choose_slot,
                )
                slots_grid.add_widget(slot_btn)

        day_row.add_widget(
            Button(
                text="<",
                size_hint_x=None,
                width=56,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                on_press=lambda *_: (
                    selected_date.__setitem__("value", selected_date["value"] - timedelta(days=1)),
                    refresh_slots(),
                ),
            )
        )
        day_row.add_widget(day_label)
        day_row.add_widget(
            Button(
                text=">",
                size_hint_x=None,
                width=56,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                on_press=lambda *_: (
                    selected_date.__setitem__("value", selected_date["value"] + timedelta(days=1)),
                    refresh_slots(),
                ),
            )
        )
        root.add_widget(day_row)

        refresh_slots()


        actions = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=44)

        def submit(*_):
            dt = selected_dt["value"]
            if dt is None:
                show_modal("Выберите время приёма")
                return

            self.run_async(
                create_appointment(self.manager.current_user_id, doctor.id, dt),
                lambda *_: self._after_patient_book(modal),
                lambda msg: show_modal(msg),
            )

        actions.add_widget(
            Button(
                text="Записаться",
                on_press=submit,
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
            )
        )
        actions.add_widget(
            Button(
                text="Отмена",
                on_press=lambda *_: modal.dismiss(),
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
            )
        )
        root.add_widget(actions)
        modal.add_widget(root)
        modal.open()

    def _after_patient_book(self, modal: ModalView):
        modal.dismiss()
        show_modal("Вы успешно записаны")

    def _open_patient_appointments(self):
        self.run_async(
            get_patient_appointments(self.manager.current_user_id),
            lambda appointments: self._show_appointments_modal(appointments, "Мои приёмы", StorageStatus.PATIENT),
            lambda msg: show_modal(msg),
        )

    def _open_admin_doctor_appointments(self):
        doctor = self._selected_doctor()
        if doctor is None:
            show_modal("Выберите врача")
            return

        self.run_async(
            get_appointments_by_doctor_id(doctor.id),
            lambda appointments: self._show_appointments_modal(
                appointments,
                f"Приёмы врача: {doctor.fio}",
                StorageStatus.ADMIN,
            ),
            lambda msg: show_modal(msg),
        )

    def _show_appointments_modal(self, appointments: list[AppointmentView], title: str, role: StorageStatus):
        modal = ModalView(size_hint=(0.9, 0.85), auto_dismiss=False)
        root = BoxLayout(orientation="vertical", spacing=10, padding=12)
        root.add_widget(Label(text=title, color=self.conf.text_color, size_hint_y=None, height=34, font_size="20sp"))

        scroll = ScrollView()
        list_layout = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        list_layout.bind(minimum_height=list_layout.setter("height"))
        scroll.add_widget(list_layout)

        if not appointments:
            list_layout.add_widget(Label(text="Записей пока нет", color=self.conf.hint_color, size_hint_y=None, height=34))

        for appointment in appointments:
            status_label = STATUS_LABELS.get(appointment.status, appointment.status.value)
            btn = Button(
                text=f"{appointment.dt.strftime('%d.%m.%Y %H:%M')} | {appointment.doctor_fio} | {status_label}",
                size_hint_y=None,
                height=48,
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                on_press=lambda _, a=appointment, r=role: self._open_appointment_details(a, r),
            )
            list_layout.add_widget(btn)

        root.add_widget(scroll)
        root.add_widget(
            Button(
                text="Закрыть",
                size_hint_y=None,
                height=44,
                on_press=lambda *_: modal.dismiss(),
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
            )
        )
        modal.add_widget(root)
        modal.open()

    def _open_doctor_form(self, doctor: DoctorView | None = None):
        is_edit = doctor is not None
        modal = ModalView(size_hint=(0.8, 0.65), auto_dismiss=False)
        root = BoxLayout(orientation="vertical", padding=16, spacing=10)
        root.add_widget(
            Label(
                text="Изменение врача" if is_edit else "Добавление врача",
                color=self.conf.text_color,
                size_hint_y=None,
                height=36,
                font_size="20sp",
            )
        )

        login_input = TextInput(hint_text="Логин", multiline=False, size_hint_y=None, height=44, text="")
        password_input = TextInput(
            hint_text="Пароль",
            multiline=False,
            password=True,
            size_hint_y=None,
            height=44,
            text="",
        )
        fio_input = TextInput(
            hint_text="ФИО врача",
            multiline=False,
            size_hint_y=None,
            height=44,
            text="" if not is_edit else doctor.fio,
        )
        spec_input = TextInput(
            hint_text="Специализация",
            multiline=False,
            size_hint_y=None,
            height=44,
            text="" if not is_edit else doctor.specialization,
        )

        root.add_widget(login_input)
        root.add_widget(password_input)
        root.add_widget(fio_input)
        root.add_widget(spec_input)

        if is_edit:
            login_input.hint_text = "Новый логин (пусто = без изменений)"
            password_input.hint_text = "Новый пароль (пусто = без изменений)"

        actions = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=44)

        def submit(*_):
            if is_edit:
                self.run_async(
                    update_doctor(doctor.id, fio_input.text, spec_input.text, login_input.text, password_input.text),
                    lambda *_: self._after_doctor_saved(modal, "Данные врача обновлены"),
                    lambda msg: show_modal(msg),
                )
            else:
                self.run_async(
                    create_doctor(login_input.text, password_input.text, fio_input.text, spec_input.text),
                    lambda *_: self._after_doctor_saved(modal, "Врач добавлен"),
                    lambda msg: show_modal(msg),
                )

        actions.add_widget(
            Button(
                text="Сохранить",
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                on_press=submit,
            )
        )
        actions.add_widget(
            Button(
                text="Отмена",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                on_press=lambda *_: modal.dismiss(),
            )
        )
        root.add_widget(actions)

        modal.add_widget(root)
        modal.open()

    def _after_doctor_saved(self, modal: ModalView, message: str):
        modal.dismiss()
        self.refresh()
        show_modal(message)

    def _confirm_delete(self):
        doctor = self._selected_doctor()
        if doctor is None:
            show_modal("Выберите врача")
            return

        show_confirm_modal(
            text=f"Удалить врача {doctor.fio}?",
            on_yes=lambda: self.run_async(
                delete_doctor(doctor.id),
                lambda *_: self._after_delete(),
                lambda msg: show_modal(msg),
            ),
        )

    def _after_delete(self):
        self.refresh()
        show_modal("Врач удален")

    def _open_appointment_details(self, appointment: AppointmentView, role: StorageStatus):
        from src.ui.screens.doctor_placeholder import open_appointment_modal

        open_appointment_modal(parent=self, appointment=appointment, role=role, on_saved=None)
