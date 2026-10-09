from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

from . import CODENAME, EXPANSION, __version__
from .brain import Brain
from .config import Settings
from .events import EventBus
from .executor import Executor
from .server import HudServer
from .speech.listener import Listener, split_wake_word
from .speech.speaker import Speaker
from .telemetry import TelemetryFeed
from .ui.tray import Tray
from .ui.window import HudWindow

log = logging.getLogger(__name__)


class Simon:
    def __init__(self, settings: Settings, window_mode: str = "native", use_mic: bool = True, muted: bool = False):
        self.settings = settings
        self.name = settings.get("assistant.name", "Simon")
        self.bus = EventBus()
        self.speaker = Speaker(settings, self.bus, muted=muted)
        self.listener = Listener(settings, self.bus)
        self.brain = Brain(settings, self.bus, say=self.say_async)
        self.executor = Executor(self.bus, on_hide=self._request_hide)
        self.telemetry = TelemetryFeed(self.bus)
        self.server = HudServer(
            self.bus,
            api={
                "command": lambda b: self.submit(str(b.get("text", "")), voice=False),
                "activate": lambda b: self.activate(),
                "stop": lambda b: self.speaker.stop(),
                "hide": lambda b: self.hide(),
                "minimize": lambda b: self.window.minimize(),
                "fullscreen": lambda b: self.window.toggle_fullscreen(),
                "quit": lambda b: self.quit(),
            },
            host=settings.get("hud.host", "127.0.0.1"),
            port=settings.get("hud.port", 47800),
        )
        self.window: Optional[HudWindow] = None
        self.window_mode = window_mode
        self.tray = Tray(self.name, on_open=self.show, on_talk=self.activate, on_pause=self._set_paused, on_quit=self.quit)
        self.use_mic = use_mic

        self.state = "booting"
        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        self._busy = threading.Event()
        self._paused = False
        self._stop = threading.Event()
        self._hide_timer: Optional[threading.Timer] = None
        self._hide_requested = False
        self._last_activation = 0.0

    def run(self) -> None:
        self.server.start()
        self.window = HudWindow(self.server.url, self.settings, mode=self.window_mode)
        self.window.run(on_ready=self._boot)
        self.quit()

    def _boot(self) -> None:
        self.bus.publish("config", version=__version__, codename=CODENAME, expansion=EXPANSION, **self.settings.public())
        self._set_state("booting")
        self.telemetry.start()
        self.brain.start()
        self.tray.start()
        threading.Thread(target=self._worker, name="worker", daemon=True).start()

        mic_ok = False
        if self.use_mic:
            try:
                self.listener.start()
                mic_ok = True
            except Exception as exc:
                log.warning("Microphone unavailable (%s) — text input only", exc)
                self.bus.publish("notify", level="warn", title="NO MICROPHONE", text="Voice input offline. Type commands below.")
        self.bus.publish("status", mic="online" if mic_ok else "offline")
        if mic_ok:
            self._register_hotkey()
            if self.settings.get("listening.wake_word_enabled", True):
                threading.Thread(
                    target=self.listener.wake_loop,
                    args=(self._on_wake, lambda: not self._paused and not self._busy.is_set(), self._stop),
                    name="wake-word",
                    daemon=True,
                ).start()

        time.sleep(3.2)
        self._set_state("idle")
        user = getattr(self.brain.skills.get("knowledge"), "user_name", "") or "sir"
        self.say_async(f"{self.name} online. All systems nominal. Welcome back, {user}.")
        self._schedule_hide()

    def _register_hotkey(self) -> None:
        hotkey = self.settings.get("listening.hotkey")
        if not hotkey:
            return
        try:
            import keyboard

            keyboard.add_hotkey(hotkey, self.activate, suppress=False)
            log.info("Hotkey armed: %s", hotkey)
        except Exception as exc:
            log.warning("Could not register hotkey %s: %s", hotkey, exc)

    def _set_state(self, state: str, **extra) -> None:
        self.state = state
        self.bus.publish("state", state=state, **extra)

    def _set_paused(self, paused: bool) -> None:
        self._paused = paused
        self.bus.publish("status", mic="paused" if paused else "online")

    def activate(self) -> None:
        now = time.monotonic()
        if now - self._last_activation < 0.6:
            return
        self._last_activation = now
        if self.speaker.busy:
            self.speaker.stop()
        elif self._busy.is_set():
            return
        self._jobs.put(("listen", None))

    def _on_wake(self, command: str) -> None:
        if command:
            self._jobs.put(("text", command, True))
        else:
            self._jobs.put(("listen", None))

    def submit(self, text: str, voice: bool = False) -> bool:
        text = text.strip()
        if not text:
            return False
        self._jobs.put(("text", text, voice))
        return True

    def say_async(self, text: str) -> None:
        self._jobs.put(("say", text))

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            self._busy.set()
            self._cancel_hide()
            self.show()
            try:
                kind = job[0]
                if kind == "listen":
                    self._listen_and_handle()
                elif kind == "text":
                    self._handle(job[1], voice=job[2])
                elif kind == "say":
                    self._speak(job[1])
            except Exception:
                log.exception("Job %s failed", job[0])
                self._set_state("error")
                self._speak("Something went wrong. I've logged the details.")
            finally:
                self._busy.clear()
                if self._jobs.empty():
                    self._set_state("idle")
                    self._schedule_hide()

    def _listen_and_handle(self, follow_up: bool = False) -> None:
        if not self.listener.ready:
            self.bus.publish("notify", level="warn", title="NO MICROPHONE", text="Type your command instead.")
            return
        self._set_state("listening", follow_up=follow_up)
        self.bus.publish("sfx", name="listen")
        timeout = self.settings.get("listening.conversation_window" if follow_up else "listening.command_timeout", 6)
        text = self.listener.listen(timeout=timeout, phrase_limit=self.settings.get("listening.phrase_limit", 12))
        if not text:
            self.bus.publish("sfx", name="cancel")
            return
        found, rest = split_wake_word(text, self.settings.get("listening.wake_words", []))
        self._handle(rest if found and rest else text, voice=True)

    def _handle(self, text: str, voice: bool) -> None:
        log.info("» %s", text)
        self.bus.publish("transcript", role="user", text=text, voice=voice)
        self._set_state("thinking")
        started = time.perf_counter()
        plan = self.brain.think(text)
        latency = int((time.perf_counter() - started) * 1000)

        response = plan.response
        if plan.actions:
            results = self.executor.run(plan.actions)
            failures = [r for r in results if not r.ok]
            if failures:
                response = failures[0].message or "I'm afraid I couldn't do that."
        log.info("« %s  [%s, %d ms]", response, plan.source, latency)
        self.bus.publish("transcript", role="assistant", text=response, source=plan.source, latency=latency,
                         actions=[a.as_dict() for a in plan.actions])
        self._speak(response)
        if self._hide_requested:
            self._hide_requested = False
            self.hide()
        elif voice and plan.expect_reply and self.listener.ready:
            self._listen_and_handle(follow_up=True)

    def _speak(self, text: str) -> None:
        self._set_state("speaking", text=text)
        self.speaker.speak(text)

    def show(self) -> None:
        if self.window:
            self.window.show()
        self.bus.publish("visibility", visible=True)

    def _request_hide(self) -> None:
        self._hide_requested = True

    def hide(self) -> None:
        self.bus.publish("visibility", visible=False)
        if self.window:
            threading.Timer(0.9, self.window.hide).start()

    def _schedule_hide(self) -> None:
        self._cancel_hide()
        if not self.settings.get("hud.auto_hide", True):
            return
        self._hide_timer = threading.Timer(self.settings.get("hud.auto_hide_delay", 8.0), self._auto_hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()

    def _auto_hide(self) -> None:
        if not self._busy.is_set() and self._jobs.empty():
            self.hide()

    def _cancel_hide(self) -> None:
        if self._hide_timer:
            self._hide_timer.cancel()
            self._hide_timer = None

    def quit(self) -> None:
        if self._stop.is_set():
            return
        log.info("Shutting down")
        self._stop.set()
        self.speaker.stop()
        self.telemetry.stop()
        self.tray.stop()
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:
            pass
        if self.window:
            self.window.quit()
        self.server.stop()
