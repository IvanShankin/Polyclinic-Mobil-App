from typing import Callable, Optional

from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock


def show_confirm_modal(
    text: str,
    on_yes: Optional[Callable[[], None]] = None,
    on_no: Optional[Callable[[], None]] = None,
):
    modal = ModalView(
        size_hint=(0.8, 0.6),
        auto_dismiss=False
    )

    root = BoxLayout(
        orientation="vertical",
        padding=20,
        spacing=15
    )

    # ===== Scrollable текст =====
    scroll = ScrollView(size_hint=(1, 1))

    label = Label(
        text=text,
        size_hint_y=None,
        halign="left",
        valign="top",
    )

    label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
    scroll.bind(width=lambda inst, val: setattr(label, "text_size", (val - 20, None)))

    scroll.add_widget(label)

    # ===== Кнопки =====
    buttons = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=45,
        spacing=15
    )

    btn_yes = Button(
        text="Да",
        background_normal='',
        background_color=(0.2, 0.6, 0.2, 1)
    )

    btn_no = Button(
        text="Нет",
        background_normal='',
        background_color=(0.8, 0.2, 0.2, 1)
    )

    def yes_handler(*_):
        modal.dismiss()
        if on_yes:
            on_yes()

    def no_handler(*_):
        modal.dismiss()
        if on_no:
            on_no()

    btn_yes.bind(on_release=yes_handler)
    btn_no.bind(on_release=no_handler)

    # Поменяли порядок кнопок
    buttons.add_widget(btn_yes)
    buttons.add_widget(btn_no)

    root.add_widget(scroll)
    root.add_widget(buttons)

    modal.add_widget(root)

    Clock.schedule_once(
        lambda dt: setattr(label, "text_size", (scroll.width - 20, None))
    )

    modal.open()
