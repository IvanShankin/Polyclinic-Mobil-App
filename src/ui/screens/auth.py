from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

from src.config import get_config
from src.service.database.actions import login_user, register_patient
from src.service.database.models import StorageStatus
from src.ui.screens.base import DarkScreen
from src.ui.screens.modal_window.modal_with_ok import show_modal
from src.ui.screens.screen_manager import RootScreenManager

# Темная палитра
Window.clearcolor = (0.15, 0.15, 0.15, 1)

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conf = get_config()

        self.padding = [12, 12, 12, 12]
        self.font_size = 16
        self.background_color = self.conf.input_dg
        self.foreground_color = self.conf.text_color
        self.hint_text_color = self.conf.hint_color
        self.multiline = False
        self.cursor_color = self.conf.text_color
        self.background_normal = ''
        self.background_active = ''


class AuthScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "auth"
        self.conf = get_config()

        # Внешний AnchorLayout центрирует форму
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        self.add_widget(anchor)

        # Сама форма
        form = BoxLayout(orientation='vertical', spacing=12, padding=20,
                         size_hint=(0.8, None))  # ширина 80% окна, высота под контент
        form.bind(minimum_height=form.setter('height'))  # авто-рост по содержимому
        anchor.add_widget(form)

        form.add_widget(Label(text="Авторизация", font_size=24, bold=True, color=self.conf.text_color,
                              size_hint_y=None, height=40))

        form.add_widget(Label(text="Логин", size_hint_y=None, height=25, color=self.conf.text_color))
        self.login = StyledTextInput(hint_text="Введите логин", size_hint_y=None, height=45)
        form.add_widget(self.login)

        form.add_widget(Label(text="Пароль", size_hint_y=None, height=25, color=self.conf.text_color))
        self.password = StyledTextInput(password=True, hint_text="Введите пароль", size_hint_y=None, height=45)
        form.add_widget(self.password)

        form.add_widget(Button(text="Войти", size_hint_y=None, height=45,
                               background_color=self.conf.primary_btn, color=self.conf.text_color,
                               on_press=self.do_login))
        form.add_widget(Button(text="Регистрация пациента", size_hint_y=None, height=45,
                               background_color=self.conf.secondary_btn, color=self.conf.text_color,
                               on_press=self.to_register))


    def do_login(self, *_):
        self.set_message("Выполняется вход...")
        self.run_async(login_user(self.login.text, self.password.text), self._after_login)

    def _after_login(self, payload):
        sm: RootScreenManager = self.manager
        sm.current_user_id = payload.user_id
        sm.current_role = payload.role
        self.set_message("Успешный вход")
        if payload.role == StorageStatus.ADMIN:
            sm.get_screen("admin").refresh()
            sm.safe_switch("admin")
        elif payload.role == StorageStatus.PATIENT:
            sm.get_screen("patient").refresh()
            sm.safe_switch("patient")
        elif payload.role == StorageStatus.DOCTOR:
            sm.get_screen("doctor").refresh()
            sm.safe_switch("doctor")

    def to_register(self, *_):
        self.manager.safe_switch("register")


class RegisterScreen(DarkScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "register"
        self.conf = get_config()

        # Внешний AnchorLayout центрирует форму
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        self.add_widget(anchor)

        # Сама форма
        form = BoxLayout(orientation='vertical', spacing=12, padding=20,
                         size_hint=(0.8, None))  # ширина 80% окна, высота под контент
        form.bind(minimum_height=form.setter('height'))  # авто-рост по содержимому
        anchor.add_widget(form)

        form.add_widget(Label(text="Регистрация", font_size=24, size_hint_y=None, height=40, bold=True, color=self.conf.text_color))

        form.add_widget(Label(text="Логин", size_hint_y=None, height=25, color=self.conf.text_color))
        self.login = StyledTextInput(hint_text="Введите логин", size_hint_y=None, height=45)
        form.add_widget(self.login)

        form.add_widget(Label(text="Пароль", size_hint_y=None, height=25, color=self.conf.text_color))
        self.password = StyledTextInput(password=True, hint_text="Введите пароль", size_hint_y=None, height=45)
        form.add_widget(self.password)

        form.add_widget(Label(text="ФИО", size_hint_y=None, height=25, color=self.conf.text_color))
        self.fio = StyledTextInput(hint_text="Введите ФИО", size_hint_y=None, height=45)
        form.add_widget(self.fio)

        form.add_widget(Label(text="Телефон", size_hint_y=None, height=25, color=self.conf.text_color))
        self.phone = StyledTextInput(hint_text="Введите телефон", size_hint_y=None, height=45)
        form.add_widget(self.phone)

        form.add_widget(Button(text="Зарегистрироваться", size_hint_y=None, height=45,
                                      background_color=self.conf.primary_btn, color=self.conf.text_color,
                                      on_press=self.register))

        form.add_widget(Button(text="Назад", size_hint_y=None, height=45,
                                      background_color=self.conf.secondary_btn, color=self.conf.text_color,
                                      on_press=lambda *_: self.manager.safe_switch("auth")))

    def register(self, *_):
        self.run_async(
            register_patient(self.login.text, self.password.text, self.fio.text, self.phone.text),
            lambda _: self._done(),
            lambda error_msg: self._error_reg(error_msg),
        )

    def _done(self):
        show_modal("Регистрация завершена. Войдите в систему.")

    def _error_reg(self, error_msg: str):
        show_modal(error_msg)
