from __future__ import annotations

import asyncio
import logging
import math
import os
import queue
import random
import tempfile
import threading
import time
import wave
from typing import Iterator, List, Optional

from ..config import VOICES_DIR, Settings
from ..events import EventBus
from . import kokoro
from .kokoro import KokoroVoice

log = logging.getLogger(__name__)

FPS = 30
ENGINES = ("kokoro", "edge", "piper", "system")


class Speaker:
    def __init__(self, settings: Settings, bus: EventBus, muted: bool = False):
        self.settings = settings
        self.bus = bus
        self.muted = muted
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._piper = None
        self._kokoro: Optional[KokoroVoice] = None
        self._engine = ""

    def start(self) -> None:
        threading.Thread(target=self._prepare_kokoro, name="kokoro-prep", daemon=True).start()

    def speak(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._stop.clear()
            try:
                if self.muted:
                    self._simulate(text)
                    return
                spoke = False
                for path in self._render(text):
                    try:
                        if not self._stop.is_set():
                            self._play(path)
                            spoke = True
                    finally:
                        _remove(path)
                if not spoke and not self._stop.is_set():
                    self._simulate(text)
            finally:
                self.bus.publish("level", source="voice", value=0.0)

    def stop(self) -> None:
        self._stop.set()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def _order(self) -> List[str]:
        engine = self.settings.get("voice.engine", "auto")
        if engine in ENGINES:
            return [engine]
        return list(ENGINES)

    def _render(self, text: str) -> Iterator[str]:
        for name in self._order():
            try:
                if name == "kokoro":
                    stream = self._kokoro_stream(text)
                    first = next(stream)
                    self._announce("kokoro")
                    yield first
                    yield from stream
                    return
                path = getattr(self, f"_tts_{name}")(text)
                if path and os.path.getsize(path) > 0:
                    self._announce(name)
                    yield path
                    return
                _remove(path)
            except StopIteration:
                return
            except Exception as exc:
                log.debug("TTS engine %s unavailable: %s", name, exc)
        log.warning("No TTS engine available — speaking silently")

    def _announce(self, engine: str) -> None:
        if engine == self._engine:
            return
        self._engine = engine
        label = {
            "kokoro": f"Kokoro · {self.settings.get('voice.kokoro_voice', 'bm_george')[3:].title()}",
            "edge": self.settings.get("voice.edge_voice", "en-GB-RyanNeural").split("-")[-1].replace("Neural", ""),
            "piper": "Piper · Offline",
            "system": "System",
        }[engine]
        self.bus.publish("status", voice=label)

    def _kokoro_voice(self) -> KokoroVoice:
        if self._kokoro is None:
            if not kokoro.available():
                raise ImportError("kokoro-onnx is not installed")
            self._kokoro = KokoroVoice(
                self.settings.get("voice.kokoro_voice", "bm_george"),
                float(self.settings.get("voice.kokoro_speed", 1.0)),
            )
        self._kokoro.load()
        return self._kokoro

    def _prepare_kokoro(self) -> None:
        if "kokoro" not in self._order() or not kokoro.available():
            return
        try:
            if not kokoro.installed():
                self.bus.publish("notify", level="info", title="VOICE UPGRADE",
                                 text="Downloading the Kokoro offline voice (~350 MB) in the background.")
                kokoro.download()
                self.bus.publish("notify", level="info", title="VOICE UPGRADE", text="Kokoro voice installed.")
            self._kokoro_voice()
            log.info("Kokoro voice ready")
        except Exception as exc:
            log.warning("Kokoro voice unavailable: %s", exc)

    def _kokoro_stream(self, text: str) -> Iterator[str]:
        voice = self._kokoro_voice()
        chunks: "queue.Queue[object]" = queue.Queue(maxsize=3)

        def produce() -> None:
            try:
                for samples, rate in voice.stream(text):
                    if self._stop.is_set():
                        break
                    chunks.put(_write_wav(samples, rate))
            except Exception as exc:
                chunks.put(exc)
            finally:
                chunks.put(None)

        threading.Thread(target=produce, name="kokoro-tts", daemon=True).start()
        first = True
        try:
            while True:
                item = chunks.get()
                if item is None:
                    return
                if isinstance(item, Exception):
                    if first:
                        raise item
                    log.warning("Kokoro stopped mid-sentence: %s", item)
                    return
                first = False
                yield item
        finally:
            while True:
                try:
                    item = chunks.get_nowait()
                except queue.Empty:
                    break
                if isinstance(item, str):
                    _remove(item)

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

    def _play(self, path: str) -> None:
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


def _write_wav(samples, rate: int) -> str:
    import numpy as np

    path = _temp(".wav")
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return path


def _temp(suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix="simon_", suffix=suffix)
    os.close(fd)
    return path


def _remove(path: Optional[str]) -> None:
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass
