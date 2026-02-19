import asyncio
import threading
from asyncio import AbstractEventLoop

from kivy.app import App
from kivy.uix.screenmanager import FadeTransition

from src.config import get_config
from src.service.utils.event_loop import start_loop
from src.ui.screens.auth import AuthScreen, RegisterScreen
from src.ui.screens.screen_manager import RootScreenManager


class AuthApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loop: AbstractEventLoop = None

    def build(self):
        conf = get_config()

        sm = RootScreenManager(transition=FadeTransition(duration=0.15))
        self.loop = asyncio.get_event_loop()

        t = threading.Thread(target=start_loop, args=(conf.global_event_loop,), daemon=True)
        t.start()

        sm.add_widget(AuthScreen())
        sm.add_widget(RegisterScreen())

        sm.current = "auth"
        return sm
