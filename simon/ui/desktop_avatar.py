from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Callable

from ..config import DATA_DIR
from ..events import Event, EventBus
from .hologram import KEY, HologramRenderer

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 170, 210
FRAME_MS = 40
POSITION_FILE = os.path.join(DATA_DIR, "desktop_avatar.json")


class DesktopAvatar:
    def __init__(self, bus: EventBus, on_talk: Callable[[], None], on_open: Callable[[], None]):
        self.on_talk = on_talk
        self.on_open = on_open
        self.state = "idle"
        self.level = 0.0
        self.wanted = False
        self._shown = False
        self._stop = threading.Event()
        self._root = None
        bus.on(self._on_event)

    def _on_event(self, e: Event) -> None:
        kind = e["type"]
        if kind == "state":
            self.state = e["state"]
        elif kind == "level" and (e.get("source") == "voice" or self.state == "listening"):
            self.level = float(e.get("value", 0.0))
        elif kind == "visibility":
            self.wanted = not e["visible"]

    def start(self) -> None:
        threading.Thread(target=self._run, name="desktop-avatar", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            import tkinter as tk

            from PIL import ImageTk
        except ImportError as exc:
            log.info("Desktop avatar unavailable: %s", exc)
            return
        try:
            root = tk.Tk()
        except Exception as exc:
            log.info("Desktop avatar unavailable: %s", exc)
            return
        self._root = root
        key = "#%02x%02x%02x" % KEY
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=key)
        try:
            root.attributes("-transparentcolor", key)
        except tk.TclError:
            pass
        scale = max(1.0, root.winfo_fpixels("1i") / 96)
        width, height = int(WIDTH * scale), int(HEIGHT * scale)
        x, y = self._load_position(root, width, height)
        root.geometry(f"{width}x{height}+{x}+{y}")
        label = tk.Label(root, bg=key, bd=0, highlightthickness=0, cursor="hand2")
        label.pack()
        root.withdraw()

        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Talk", command=self.on_talk)
        menu.add_command(label="Open HUD", command=self.on_open)

        drag = {"x": 0, "y": 0, "moved": False}

        def press(ev):
            drag.update(x=ev.x, y=ev.y, moved=False)

        def motion(ev):
            nx, ny = root.winfo_x() + ev.x - drag["x"], root.winfo_y() + ev.y - drag["y"]
            if abs(ev.x - drag["x"]) + abs(ev.y - drag["y"]) > 3:
                drag["moved"] = True
            root.geometry(f"+{nx}+{ny}")

        def release(_):
            if drag["moved"]:
                self._save_position(root.winfo_x(), root.winfo_y())
            else:
                self.on_talk()

        label.bind("<ButtonPress-1>", press)
        label.bind("<B1-Motion>", motion)
        label.bind("<ButtonRelease-1>", release)
        label.bind("<Double-Button-1>", lambda _: self.on_open())
        label.bind("<Button-3>", lambda ev: menu.tk_popup(ev.x_root, ev.y_root))

        renderer = HologramRenderer(width, height)
        start = time.monotonic()

        def tick():
            if self._stop.is_set():
                root.destroy()
                return
            if self.wanted != self._shown:
                self._shown = self.wanted
                if self._shown:
                    root.deiconify()
                    root.attributes("-topmost", True)
                else:
                    root.withdraw()
            if self._shown:
                frame = renderer.render(time.monotonic() - start, self.state, self.level)
                label.image = ImageTk.PhotoImage(frame)
                label.configure(image=label.image)
            root.after(FRAME_MS, tick)

        tick()
        root.mainloop()

    def _load_position(self, root, width: int, height: int) -> tuple:
        try:
            with open(POSITION_FILE, "r", encoding="utf-8") as f:
                pos = json.load(f)
            return int(pos["x"]), int(pos["y"])
        except (OSError, ValueError, KeyError):
            return root.winfo_screenwidth() - width - 32, root.winfo_screenheight() - height - 72

    def _save_position(self, x: int, y: int) -> None:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(POSITION_FILE, "w", encoding="utf-8") as f:
                json.dump({"x": x, "y": y}, f)
        except OSError:
            pass
