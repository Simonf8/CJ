from __future__ import annotations

import logging
import os
import threading
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter

from ..config import CONFIG_DIR

log = logging.getLogger(__name__)


def reactor_icon(size: int = 64, color=(0, 229, 255)) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([c - s * 0.3, c - s * 0.3, c + s * 0.3, c + s * 0.3], fill=color + (160,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(s * 0.08)))
    d = ImageDraw.Draw(img)
    for r, w in ((0.46, 0.035), (0.34, 0.05)):
        d.ellipse([c - s * r, c - s * r, c + s * r, c + s * r], outline=color + (255,), width=int(s * w))
    for i in range(10):
        start = i * 36
        d.arc([c - s * 0.4, c - s * 0.4, c + s * 0.4, c + s * 0.4], start, start + 22, fill=color + (230,), width=int(s * 0.05))
    d.ellipse([c - s * 0.14, c - s * 0.14, c + s * 0.14, c + s * 0.14], fill=(220, 252, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


class Tray:
    def __init__(self, name: str, on_open: Callable[[], None], on_talk: Callable[[], None],
                 on_pause: Callable[[bool], None], on_quit: Callable[[], None]):
        self.name = name
        self.on_open = on_open
        self.on_talk = on_talk
        self.on_pause = on_pause
        self.on_quit = on_quit
        self.paused = False
        self._icon = None

    def start(self) -> None:
        try:
            import pystray
        except ImportError:
            log.info("pystray not installed — no tray icon")
            return
        from ..startup import is_enabled, toggle

        def toggle_pause(icon, item):
            self.paused = not self.paused
            self.on_pause(self.paused)
            icon.icon = reactor_icon(color=(255, 170, 0) if self.paused else (0, 229, 255))

        menu = pystray.Menu(
            pystray.MenuItem(f"Open {self.name}", lambda: self.on_open(), default=True),
            pystray.MenuItem("Talk now", lambda: self.on_talk()),
            pystray.MenuItem(lambda _: "Resume listening" if self.paused else "Pause listening", toggle_pause),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start with Windows", lambda: toggle(), checked=lambda _: is_enabled(),
                             visible=os.name == "nt"),
            pystray.MenuItem("Open config folder", lambda: _open(CONFIG_DIR)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self._icon = pystray.Icon("simon", reactor_icon(), f"{self.name} — online", menu)
        threading.Thread(target=self._icon.run, name="tray", daemon=True).start()

    def _quit(self, icon, item) -> None:
        icon.stop()
        self.on_quit()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass


def _open(path: str) -> None:
    if os.name == "nt":
        os.startfile(path)
