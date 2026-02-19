from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from src.config import get_config
from src.service.database.actions import (
    DoctorView,
    create_doctor,
    delete_doctor,
    get_doctors,
    update_doctor,
)
from src.service.database.models import StorageStatus
from src.ui.screens.base import DarkScreen
from src.ui.screens.modal_window.modal_with_ok import show_modal
from src.ui.screens.modal_window.modal_yes_or_no import show_confirm_modal


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

        if self.role == StorageStatus.ADMIN:
            self.name = "admin"
            title = "Панель администратора"
        else:
            self.name = "patient"
            title = "Кабинет пациента"

        anchor = AnchorLayout(anchor_x="center", anchor_y="top", padding=16)
        self.add_widget(anchor)

        container = BoxLayout(
            orientation="vertical",
            spacing=12,
            padding=16,
            size_hint=(0.95, 0.96),
        )
        anchor.add_widget(container)

        top_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=8)
        self.logout_btn = Button(
            text="Выйти",
            size_hint=(None, None),
            width=100,
            height=36,
            background_color=self.conf.secondary_btn,
            color=self.conf.text_color,
            on_press=lambda *_: self.manager.safe_switch("auth"),
        )
        self.refresh_btn = Button(
            text="Обновить",
            size_hint=(None, None),
            width=110,
            height=36,
            background_color=self.conf.primary_btn,
            color=self.conf.text_color,
            on_press=lambda *_: self.refresh(),
        )
        top_bar.add_widget(self.logout_btn)
        top_bar.add_widget(
            Label(
                text=title,
                font_size="24sp",
                bold=True,
                color=self.conf.text_color,
            )
        )
        top_bar.add_widget(self.refresh_btn)
        container.add_widget(top_bar)

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

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.doctors_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.doctors_layout.bind(minimum_height=self.doctors_layout.setter("height"))
        scroll.add_widget(self.doctors_layout)
        container.add_widget(scroll)

        self.action_row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=40)
        self._build_action_buttons()
        container.add_widget(self.action_row)

    def on_pre_enter(self, *_):
        self.refresh()

    def _build_action_buttons(self):
        self.action_row.clear_widgets()
        if self.role == StorageStatus.ADMIN:
            self.btn_add = Button(
                text="Добавить врача",
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                on_press=lambda *_: self._open_doctor_form(),
            )
            self.btn_edit = Button(
                text="Изменить врача",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._open_doctor_form(self._selected_doctor()),
            )
            self.btn_delete = Button(
                text="Удалить врача",
                background_color=(0.7, 0.2, 0.2, 1),
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: self._confirm_delete(),
            )
            self.action_row.add_widget(self.btn_add)
            self.action_row.add_widget(self.btn_edit)
            self.action_row.add_widget(self.btn_delete)
        else:
            self.btn_book = Button(
                text="Записаться на приём",
                background_color=self.conf.primary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: show_modal("Экран записи будет добавлен следующим шагом."),
            )
            self.btn_my_appointments = Button(
                text="Мои записи",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                disabled=True,
                on_press=lambda *_: show_modal("Экран списка записей будет добавлен следующим шагом."),
            )
            self.action_row.add_widget(self.btn_book)
            self.action_row.add_widget(self.btn_my_appointments)

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
                Label(
                    text="Врачи не найдены",
                    color=self.conf.hint_color,
                    size_hint_y=None,
                    height=40,
                )
            )
            self._update_action_buttons_state()
            return

        for doctor in doctors:
            card = BoxLayout(
                orientation="vertical",
                spacing=4,
                padding=10,
                size_hint_y=None,
                height=92,
            )
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
        else:
            self.btn_book.disabled = not selected
            self.btn_my_appointments.disabled = not selected

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

        login_input = TextInput(
            hint_text="Логин",
            multiline=False,
            size_hint_y=None,
            height=44,
            disabled=False,
            text="",
        )
        password_input = TextInput(
            hint_text="Пароль",
            multiline=False,
            password=True,
            size_hint_y=None,
            height=44,
            disabled=False,
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


class DoctorPlaceholderScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "doctor"
        self.conf = get_config()

        layout = BoxLayout(orientation="vertical", padding=20, spacing=12)
        layout.add_widget(
            Label(
                text="Кабинет врача пока не реализован",
                color=self.conf.text_color,
                font_size="20sp",
            )
        )
        layout.add_widget(
            Button(
                text="Выйти",
                background_color=self.conf.secondary_btn,
                color=self.conf.text_color,
                size_hint_y=None,
                height=46,
                on_press=lambda *_: self.manager.safe_switch("auth"),
            )
        )
        self.add_widget(layout)
