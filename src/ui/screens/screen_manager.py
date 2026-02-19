from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import ScreenManager

from src.service.database.models import StorageStatus


class RootScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.bg = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_bg, pos=self._update_bg)
        self.current_user_id: int | None = None
        self.current_role: StorageStatus | None = None

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def safe_switch(self, screen_name):
        Clock.schedule_once(lambda dt: setattr(self, "current", screen_name))

