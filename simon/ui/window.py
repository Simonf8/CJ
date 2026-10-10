from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
import webbrowser
from typing import Callable

from ..config import Settings

log = logging.getLogger(__name__)


class HudWindow:
    def __init__(self, url: str, settings: Settings, mode: str = "native"):
        self.url = url
        self.settings = settings
        self.mode = mode
        self._window = None
        self._visible = True
        self._quit = threading.Event()

    def run(self, on_ready: Callable[[], None]) -> None:
        if self.mode == "native":
            try:
                import webview
            except ImportError:
                log.warning("pywebview not installed — falling back to browser mode")
                self.mode = "browser"
            else:
                return self._run_native(webview, on_ready)
        if self.mode == "browser":
            self._open_browser()
        threading.Thread(target=on_ready, daemon=True).start()
        try:
            while not self._quit.wait(0.5):
                pass
        except KeyboardInterrupt:
            pass

    def _run_native(self, webview, on_ready: Callable[[], None]) -> None:
        hud = self.settings.get
        self._window = webview.create_window(
            hud("assistant.name", "Simon").upper(),
            self.url,
            width=hud("hud.width", 1440),
            height=hud("hud.height", 860),
            min_size=(960, 600),
            frameless=True,
            easy_drag=False,
            on_top=hud("hud.always_on_top", True),
            fullscreen=hud("hud.fullscreen", False),
            background_color="#02050a",
            text_select=False,
        )
        webview.start(on_ready, private_mode=False, debug="--debug-hud" in sys.argv)

    def _open_browser(self) -> None:
        edge = shutil.which("msedge") or shutil.which("chrome") or shutil.which("google-chrome")
        if edge:
            w, h = self.settings.get("hud.width", 1440), self.settings.get("hud.height", 860)
            subprocess.Popen([edge, f"--app={self.url}", f"--window-size={w},{h}"])
        else:
            webbrowser.open(self.url)

    def show(self) -> None:
        if self._window and not self._visible:
            self._visible = True
            self._window.show()
            try:
                self._window.restore()
            except Exception:
                pass

    def hide(self) -> None:
        if self._window and self._visible:
            self._visible = False
            self._window.hide()

    def toggle_fullscreen(self) -> None:
        if self._window:
            self._window.toggle_fullscreen()

    def minimize(self) -> None:
        if self._window:
            self._window.minimize()

    def quit(self) -> None:
        self._quit.set()
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
