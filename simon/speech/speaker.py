from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import tempfile
import threading
import time
import wave
from typing import List, Optional

from ..config import VOICES_DIR, Settings
from ..events import EventBus

log = logging.getLogger(__name__)

FPS = 30


class Speaker:
    def __init__(self, settings: Settings, bus: EventBus, muted: bool = False):
        self.settings = settings
        self.bus = bus
        self.muted = muted
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._piper = None

    def speak(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._stop.clear()
            path = None if self.muted else self._synthesize(text)
            try:
                if path:
                    self._play(path, text)
                else:
                    self._simulate(text)
            finally:
                self.bus.publish("level", source="voice", value=0.0)
                if path:
                    _remove(path)

    def stop(self) -> None:
        self._stop.set()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def _synthesize(self, text: str) -> Optional[str]:
        engine = self.settings.get("voice.engine", "auto")
        order = {"edge": ["edge"], "piper": ["piper"], "system": ["system"]}.get(engine, ["edge", "piper", "system"])
        for name in order:
            try:
                path = getattr(self, f"_tts_{name}")(text)
                if path and os.path.getsize(path) > 0:
                    return path
            except Exception as exc:
                log.debug("TTS engine %s failed: %s", name, exc)
        log.warning("No TTS engine available — speaking silently")
        return None

    def _tts_edge(self, text: str) -> str:
        import edge_tts

        path = _temp(".mp3")
        communicate = edge_tts.Communicate(
            text,
            self.settings.get("voice.edge_voice", "en-GB-RyanNeural"),
            rate=self.settings.get("voice.rate", "+0%"),
            pitch=self.settings.get("voice.pitch", "+0Hz"),
        )
        asyncio.run(communicate.save(path))
        return path

    def _tts_piper(self, text: str) -> str:
        if self._piper is None:
            from piper import PiperVoice

            model = os.path.join(VOICES_DIR, self.settings.get("voice.piper_model", "jarvis.onnx"))
            self._piper = PiperVoice.load(model)
        path = _temp(".wav")
        with wave.open(path, "wb") as wav:
            if hasattr(self._piper, "synthesize_wav"):
                self._piper.synthesize_wav(text, wav)
            else:
                self._piper.synthesize(text, wav)
        return path

    def _tts_system(self, text: str) -> str:
        import pyttsx3

        path = _temp(".wav")
        engine = pyttsx3.init()
        engine.save_to_file(text, path)
        engine.runAndWait()
        return path

    def _play(self, path: str, text: str) -> None:
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sound = pygame.mixer.Sound(path)
        envelope = _envelope(sound) or _fake_envelope(sound.get_length())
        channel = sound.play()
        start = time.monotonic()
        while channel.get_busy() and not self._stop.is_set():
            i = int((time.monotonic() - start) * FPS)
            self.bus.publish("level", source="voice", value=envelope[i] if i < len(envelope) else 0.0)
            time.sleep(1 / FPS)
        channel.stop()

    def _simulate(self, text: str) -> None:
        duration = max(1.2, len(text) * 0.055)
        for value in _fake_envelope(duration):
            if self._stop.is_set():
                break
            self.bus.publish("level", source="voice", value=value)
            time.sleep(1 / FPS)


def _envelope(sound) -> Optional[List[float]]:
    try:
        import numpy as np
        import pygame

        samples = pygame.sndarray.array(sound).astype(np.float32)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        rate = pygame.mixer.get_init()[0]
        window = max(1, rate // FPS)
        frames = len(samples) // window
        if frames == 0:
            return None
        rms = np.sqrt(np.mean(samples[: frames * window].reshape(frames, window) ** 2, axis=1))
        peak = np.percentile(rms, 95) or 1.0
        return np.clip(np.sqrt(rms / peak), 0.0, 1.0).tolist()
    except Exception:
        return None


def _fake_envelope(duration: float) -> List[float]:
    frames = int(duration * FPS)
    phase = random.random() * 10
    out = []
    for i in range(frames):
        t = i / FPS
        syllable = abs(math.sin(t * 9.5 + phase)) * 0.6 + abs(math.sin(t * 3.1)) * 0.3
        out.append(min(1.0, syllable * random.uniform(0.75, 1.1)))
    return out


def _temp(suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix="simon_", suffix=suffix)
    os.close(fd)
    return path


def _remove(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
