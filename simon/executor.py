from __future__ import annotations

import difflib
import logging
import os
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional
from urllib.parse import quote_plus

from .events import EventBus
from .plan import Action

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

APP_ALIASES: Dict[str, str] = {
    "chrome": "chrome", "google chrome": "chrome", "browser": "msedge", "firefox": "firefox",
    "edge": "msedge", "microsoft edge": "msedge", "brave": "brave", "opera": "opera",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt", "outlook": "outlook", "onenote": "onenote",
    "vscode": "code", "vs code": "code", "visual studio code": "code", "code": "code",
    "notepad": "notepad", "notepad++": "notepad++", "terminal": "wt", "windows terminal": "wt",
    "command prompt": "cmd", "cmd": "cmd", "powershell": "powershell",
    "spotify": "spotify", "vlc": "vlc", "steam": "steam",
    "explorer": "explorer", "file explorer": "explorer", "files": "explorer", "this pc": "explorer",
    "calculator": "calc", "calc": "calc", "paint": "mspaint", "snipping tool": "snippingtool",
    "task manager": "taskmgr", "control panel": "control", "settings": "ms-settings:",
    "camera": "microsoft.windows.camera:", "store": "ms-windows-store:", "mail": "outlookmail:",
    "calendar": "outlookcal:", "clock": "ms-clock:", "weather": "bingweather:",
    "discord": "discord", "slack": "slack", "teams": "msteams:", "microsoft teams": "msteams:",
    "zoom": "zoom", "whatsapp": "whatsapp:", "obs": "obs64",
}

KNOWN_FOLDERS = {
    "downloads": "~/Downloads", "documents": "~/Documents", "desktop": "~/Desktop",
    "pictures": "~/Pictures", "music": "~/Music", "videos": "~/Videos", "home": "~",
}


@dataclass
class Result:
    ok: bool
    message: str = ""


def _open_path(path: str) -> None:
    if IS_WINDOWS:
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class Executor:
    def __init__(self, bus: EventBus, on_hide: Optional[Callable[[], None]] = None):
        self.bus = bus
        self.on_hide = on_hide
        self._volume = None
        self._shortcuts: Optional[Dict[str, str]] = None
        self._handlers: Dict[str, Callable[[Optional[str]], Result]] = {
            "open_app": self.open_app,
            "open_file": self.open_file,
            "open_url": self.open_url,
            "search_google": lambda q: self.open_url(f"https://www.google.com/search?q={quote_plus(q or '')}") if q else Result(False),
            "search_youtube": lambda q: self.open_url(f"https://www.youtube.com/results?search_query={quote_plus(q or '')}") if q else Result(False),
            "volume_up": lambda _: self.volume_step(+0.1),
            "volume_down": lambda _: self.volume_step(-0.1),
            "volume_mute": lambda _: self.volume_mute(),
            "volume_set": self.volume_set,
            "media_play_pause": lambda _: self.media_key("playpause"),
            "media_next": lambda _: self.media_key("nexttrack"),
            "media_prev": lambda _: self.media_key("prevtrack"),
            "lock_screen": lambda _: self.lock_screen(),
            "screenshot": lambda _: self.screenshot(),
            "shutdown": lambda t: self.power("shutdown", t),
            "restart": lambda t: self.power("restart", t),
            "sleep": lambda t: self.power("sleep", t),
            "cancel_shutdown": lambda _: self.power("abort", None),
            "hud_hide": lambda _: self.hide_hud(),
        }

    def run(self, actions: List[Action]) -> List[Result]:
        results = []
        for action in actions:
            handler = self._handlers.get(action.name)
            if handler is None:
                results.append(Result(False, f"I don't know how to {action.name.replace('_', ' ')}."))
                continue
            try:
                result = handler(action.target)
            except Exception as exc:
                log.exception("Action %s failed", action.name)
                result = Result(False, str(exc))
            log.info("action %s(%s) -> %s", action.name, action.target, "ok" if result.ok else "failed")
            self.bus.publish("action", name=action.name, target=action.target, ok=result.ok)
            results.append(result)
        return results

    def open_app(self, name: Optional[str]) -> Result:
        if not name:
            return Result(False, "Which application?")
        key = name.lower().strip()
        exe = APP_ALIASES.get(key, key)

        if exe.endswith(":"):
            _open_path(exe)
            return Result(True)
        found = shutil.which(exe)
        if found:
            subprocess.Popen([found], creationflags=NO_WINDOW)
            return Result(True)
        shortcut = self._find_shortcut(key)
        if shortcut:
            _open_path(shortcut)
            return Result(True)
        if IS_WINDOWS:
            proc = subprocess.run(["cmd", "/c", "start", "", exe], capture_output=True, creationflags=NO_WINDOW)
            if proc.returncode == 0:
                return Result(True)
        return Result(False, f"I couldn't find {name} on this machine.")

    def _find_shortcut(self, name: str) -> Optional[str]:
        if self._shortcuts is None:
            self._shortcuts = {}
            roots = [os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
                     os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs")] if IS_WINDOWS else []
            for root in roots:
                for folder, _, files in os.walk(root):
                    for f in files:
                        if f.lower().endswith((".lnk", ".url")):
                            self._shortcuts.setdefault(os.path.splitext(f)[0].lower(), os.path.join(folder, f))
        if not self._shortcuts:
            return None
        if name in self._shortcuts:
            return self._shortcuts[name]
        contains = sorted((k for k in self._shortcuts if name in k), key=len)
        if contains:
            return self._shortcuts[contains[0]]
        close = difflib.get_close_matches(name, list(self._shortcuts), n=1, cutoff=0.75)
        return self._shortcuts[close[0]] if close else None

    def open_file(self, path: Optional[str]) -> Result:
        if not path:
            return Result(False)
        key = path.lower().strip().removeprefix("my ").removesuffix(" folder")
        resolved = os.path.expanduser(KNOWN_FOLDERS.get(key, path))
        if not os.path.exists(resolved):
            return Result(False, f"I can't find {path}.")
        _open_path(resolved)
        return Result(True)

    def open_url(self, url: Optional[str]) -> Result:
        if not url:
            return Result(False)
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return Result(webbrowser.open(url))

    def _volume_interface(self):
        if self._volume is None:
            from pycaw.pycaw import AudioUtilities

            speakers = AudioUtilities.GetSpeakers()
            endpoint = getattr(speakers, "EndpointVolume", None)
            if endpoint is None:
                from ctypes import POINTER, cast

                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume

                iface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                endpoint = cast(iface, POINTER(IAudioEndpointVolume))
            self._volume = endpoint
        return self._volume

    def _publish_volume(self) -> None:
        try:
            vol = self._volume_interface()
            self.bus.publish("volume", level=round(vol.GetMasterVolumeLevelScalar() * 100), muted=bool(vol.GetMute()))
        except Exception:
            pass

    def volume_step(self, delta: float) -> Result:
        try:
            vol = self._volume_interface()
            level = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level + delta)), None)
        except Exception:
            return self.media_key("volumeup" if delta > 0 else "volumedown", presses=5)
        self._publish_volume()
        return Result(True)

    def volume_mute(self) -> Result:
        try:
            vol = self._volume_interface()
            vol.SetMute(not vol.GetMute(), None)
        except Exception:
            return self.media_key("volumemute")
        self._publish_volume()
        return Result(True)

    def volume_set(self, level: Optional[str]) -> Result:
        try:
            value = max(0, min(100, int(float(level or 0))))
            self._volume_interface().SetMasterVolumeLevelScalar(value / 100, None)
        except Exception:
            return Result(False, "Volume control isn't available.")
        self._publish_volume()
        return Result(True)

    def media_key(self, key: str, presses: int = 1) -> Result:
        try:
            import pyautogui

            pyautogui.press(key, presses=presses)
            return Result(True)
        except Exception:
            return Result(False, "Media keys aren't available.")

    def lock_screen(self) -> Result:
        if not IS_WINDOWS:
            return Result(False, "Locking is only supported on Windows.")
        import ctypes

        return Result(bool(ctypes.windll.user32.LockWorkStation()))

    def screenshot(self) -> Result:
        import pyautogui

        folder = os.path.expanduser("~/Pictures/Simon")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"capture_{datetime.now():%Y%m%d_%H%M%S}.png")
        pyautogui.screenshot().save(path)
        self.bus.publish("notify", level="info", title="SCREEN CAPTURED", text=path)
        return Result(True, path)

    def power(self, mode: str, delay: Optional[str]) -> Result:
        if not IS_WINDOWS:
            return Result(False, "Power control is only supported on Windows.")
        seconds = str(max(0, int(delay or 10)))
        commands = {
            "shutdown": ["shutdown", "/s", "/t", seconds],
            "restart": ["shutdown", "/r", "/t", seconds],
            "abort": ["shutdown", "/a"],
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        }
        subprocess.run(commands[mode], creationflags=NO_WINDOW)
        if mode in ("shutdown", "restart"):
            self.bus.publish("countdown", mode=mode, seconds=int(seconds))
        elif mode == "abort":
            self.bus.publish("countdown", mode="abort", seconds=0)
        return Result(True)

    def hide_hud(self) -> Result:
        if self.on_hide:
            self.on_hide()
        return Result(True)
