from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from src.config import get_config
from src.ui.screens.base import DarkScreen


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