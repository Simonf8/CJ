from __future__ import annotations

import logging
import re
import threading
import time
from typing import Callable, Iterable, Optional, Tuple

from ..config import Settings
from ..events import EventBus

log = logging.getLogger(__name__)


def split_wake_word(text: str, wake_words: Iterable[str]) -> Tuple[bool, str]:
    lowered = text.lower().strip()
    for word in sorted(wake_words, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(word.lower())}\b[\s,.!?]*", lowered)
        if m:
            return True, lowered[m.end():].strip(" ,.!?")
    return False, ""


class Listener:
    def __init__(self, settings: Settings, bus: EventBus):
        self.settings = settings
        self.bus = bus
        self.lock = threading.Lock()
        self._recognizer = None
        self._mic = None
        self._last_level = 0.0

    def start(self) -> None:
        import speech_recognition as sr

        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.7
        self._mic = sr.Microphone()
        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.8)
        log.info("Microphone calibrated (energy threshold %.0f)", self._recognizer.energy_threshold)

    @property
    def ready(self) -> bool:
        return self._mic is not None

    def listen(self, timeout: float, phrase_limit: float, active: bool = True) -> Optional[str]:
        import speech_recognition as sr

        if not self.ready:
            return None
        with self.lock:
            try:
                with self._mic as source:
                    if active:
                        self._tap(source)
                    audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
            finally:
                if active:
                    self.bus.publish("level", source="mic", value=0.0)
        try:
            return self._recognizer.recognize_google(audio, language=self.settings.get("listening.language", "en-GB"))
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            log.warning("Speech service unavailable: %s", exc)
            self.bus.publish("notify", level="warn", title="SPEECH LINK DOWN", text="Speech recognition is unreachable.")
            time.sleep(2)
            return None

    def _tap(self, source) -> None:
        stream = source.stream
        read = stream.read

        def tapped(size, *args, **kwargs):
            data = read(size, *args, **kwargs)
            self._emit_level(data)
            return data

        stream.read = tapped

    def _emit_level(self, data: bytes) -> None:
        try:
            import numpy as np

            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
        except ImportError:
            rms = 0.0
        level = min(1.0, (rms / 2500.0) ** 0.6)
        self._last_level = self._last_level * 0.55 + level * 0.45
        self.bus.publish("level", source="mic", value=round(self._last_level, 3))

    def wake_loop(self, on_wake: Callable[[str], None], enabled: Callable[[], bool], stop: threading.Event) -> None:
        wake_words = self.settings.get("listening.wake_words", ["simon"])
        log.info("Wake word listener armed: %s", ", ".join(wake_words))
        while not stop.is_set():
            if not enabled() or self.lock.locked():
                time.sleep(0.15)
                continue
            try:
                heard = self.listen(timeout=3, phrase_limit=4, active=False)
            except Exception:
                log.debug("Wake listen failed", exc_info=True)
                time.sleep(0.5)
                continue
            if not heard or not enabled():
                continue
            found, command = split_wake_word(heard, wake_words)
            if found:
                log.info("Wake word detected (%r)", heard)
                on_wake(command)
