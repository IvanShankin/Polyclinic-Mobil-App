from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from src.config import get_config


def show_modal(text: str):
    conf = get_config()
    modal = ModalView(
        size_hint=(0.7, 0.5),
        auto_dismiss=False,
        background_color=conf.dark_bg
    )

    root = BoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(15)
    )

    scroll = ScrollView(
        size_hint=(1, 1)
    )

    label = Label(
        text=text,
        size_hint=(1, None),
        halign="center",
        valign="middle",
        color=conf.text_color,
        font_size=sp(16),
    )

    # Автоматическая высота по тексту
    label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))

    scroll.bind(
        width=lambda inst, val: setattr(label, "text_size", (val - dp(20), None))
    )

    scroll.add_widget(label)

    btn = Button(
        text="OK",
        size_hint_y=None,
        height=dp(45),
        background_color=conf.primary_btn,
        color=conf.text_color
    )

    btn.bind(on_release=modal.dismiss)

    root.add_widget(scroll)
    root.add_widget(btn)

    modal.add_widget(root)

    # ���������� ��������� ������ �����
    Clock.schedule_once(lambda dt: setattr(label, "text_size", (scroll.width - dp(20), None)))

    modal.open()
