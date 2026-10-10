from __future__ import annotations

import importlib.util
import logging
import os
import re
import sys
import threading
import urllib.request
from typing import Callable, Iterator, List, Optional, Tuple

from ..config import VOICES_DIR

log = logging.getLogger(__name__)

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {"model": "kokoro-v1.0.onnx", "voices": "voices-v1.0.bin"}
KOKORO_DIR = os.path.join(VOICES_DIR, "kokoro")

_SENTENCE = re.compile(r"(?<=[.!?;:])\s+")


def path(kind: str) -> str:
    return os.path.join(KOKORO_DIR, FILES[kind])


def installed() -> bool:
    return all(os.path.exists(path(k)) for k in FILES)


def available() -> bool:
    return importlib.util.find_spec("kokoro_onnx") is not None


def download(progress: Optional[Callable[[str, float], None]] = None) -> None:
    os.makedirs(KOKORO_DIR, exist_ok=True)
    for kind, name in FILES.items():
        target = path(kind)
        if os.path.exists(target):
            continue
        tmp = target + ".part"
        with urllib.request.urlopen(RELEASE + name, timeout=30) as resp, open(tmp, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(name, done / total)
        os.replace(tmp, target)


def split_sentences(text: str, min_len: int = 12) -> List[str]:
    parts: List[str] = []
    for piece in _SENTENCE.split(text.strip()):
        if parts and len(parts[-1]) < min_len:
            parts[-1] = f"{parts[-1]} {piece}"
        elif piece:
            parts.append(piece)
    return parts


class KokoroVoice:
    def __init__(self, voice: str = "bm_george", speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self._model = None
        self._lock = threading.Lock()

    @property
    def lang(self) -> str:
        return "en-gb" if self.voice[:1] == "b" else "en-us"

    def load(self) -> None:
        with self._lock:
            if self._model is None:
                if not installed():
                    raise FileNotFoundError("Kokoro model files are not downloaded")
                from kokoro_onnx import Kokoro

                self._model = Kokoro(path("model"), path("voices"))
                self._model.create("Ready.", voice=self.voice, speed=self.speed, lang=self.lang)

    def stream(self, text: str) -> Iterator[Tuple["object", int]]:
        self.load()
        for sentence in split_sentences(text):
            samples, rate = self._model.create(sentence, voice=self.voice, speed=self.speed, lang=self.lang)
            yield samples, rate


if __name__ == "__main__":
    if installed():
        print("Kokoro voice already installed.")
        sys.exit(0)
    print("Downloading Kokoro voice model (~350 MB)…")
    last = {"pct": -1}

    def show(name: str, frac: float) -> None:
        pct = int(frac * 100)
        if pct != last["pct"] and pct % 5 == 0:
            last["pct"] = pct
            print(f"  {name}: {pct}%", flush=True)

    download(show)
    print("Done.")
