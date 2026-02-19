import asyncio
import threading
from asyncio import AbstractEventLoop

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from src.config import get_config
from src.service.utils.event_loop import start_loop


class RootScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)  # белый фон
            self.bg = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_bg, pos=self._update_bg)

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def safe_switch(self, screen_name):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self, "current", screen_name))


class AuthApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loop: AbstractEventLoop = None

    def build(self):
        conf = get_config()

        sm = RootScreenManager(transition=FadeTransition(duration=0.15))

        self.loop = asyncio.get_event_loop()


        # Запускаем глобальный event loop в отдельном потоке
        t = threading.Thread(target=start_loop, args=(conf.global_event_loop,), daemon=True)
        t.start()

        return sm
