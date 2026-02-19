import asyncio
import logging
from concurrent.futures import Future

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from src.config import get_config
from src.service.exeptions import ServiceError
from src.ui.screens.modal_window.modal_with_ok import show_modal


class BaseFormScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.message = Label(size_hint_y=None, height=40)
        self.layout.add_widget(self.message)
        self.add_widget(self.layout)

    def set_message(self, text: str):
        self.message.text = text

    def run_async(self, coro, on_success=None, on_error=None):
        loop = get_config().global_event_loop
        future: Future = asyncio.run_coroutine_threadsafe(coro, loop)

        def done_callback(done: Future):
            try:
                result = done.result()
            except ServiceError as e:
                Clock.schedule_once(lambda dt, exc=e: on_error(f"Ошибка: {str(exc)}"))
                return
            except Exception as e:
                logging.exception("Исключение: ")
                Clock.schedule_once(lambda dt, exc=e: on_error(f"Ошибка: {str(exc)}"))
                return


            if on_success:
                Clock.schedule_once(lambda dt: on_success(result))

        future.add_done_callback(done_callback)


class DarkScreen(BaseFormScreen):
    """Базовый экран с темным фоном, чтобы не моргал черный при переключении"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*get_config().dark_bg)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

    def _update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos