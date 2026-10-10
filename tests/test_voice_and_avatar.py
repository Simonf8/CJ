import os
import tempfile

import numpy as np
import pytest

from simon.speech import kokoro
from simon.speech.kokoro import split_sentences
from simon.speech.speaker import Speaker
from simon.ui.desktop_avatar import DesktopAvatar
from simon.ui.hologram import KEY, HologramRenderer


def test_split_sentences_merges_fragments():
    assert split_sentences("Good evening, sir. Diagnostics are complete. Yes. Shall I?") == [
        "Good evening, sir.", "Diagnostics are complete.", "Yes. Shall I?",
    ]


def _tmp_audio():
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.write(fd, b"RIFF")
    os.close(fd)
    return path


@pytest.fixture
def speaker(settings, bus, monkeypatch):
    sp = Speaker(settings, bus)
    sp.played = []
    monkeypatch.setattr(sp, "_play", lambda path: sp.played.append(path))
    return sp


def test_falls_back_to_edge_when_kokoro_missing(speaker, bus, monkeypatch):
    monkeypatch.setattr(kokoro, "available", lambda: False)
    monkeypatch.setattr(speaker, "_tts_edge", lambda text: _tmp_audio())
    speaker.speak("Hello there.")
    assert len(speaker.played) == 1
    assert not os.path.exists(speaker.played[0])
    assert bus.last("status")["voice"] == "Ryan"


def test_kokoro_streams_each_sentence(speaker, bus, monkeypatch):
    class FakeVoice:
        def stream(self, text):
            for _ in split_sentences(text):
                yield np.zeros(2400, dtype=np.float32), 24000

    monkeypatch.setattr(speaker, "_kokoro_voice", lambda: FakeVoice())
    speaker.speak("First sentence here. Second sentence here. Third one too.")
    assert len(speaker.played) == 3
    assert bus.last("status")["voice"].startswith("Kokoro")


def test_kokoro_failure_before_audio_uses_next_engine(speaker, monkeypatch):
    class BrokenVoice:
        def stream(self, text):
            raise RuntimeError("onnx exploded")
            yield

    monkeypatch.setattr(speaker, "_kokoro_voice", lambda: BrokenVoice())
    monkeypatch.setattr(speaker, "_tts_edge", lambda text: _tmp_audio())
    speaker.speak("Still talking.")
    assert len(speaker.played) == 1


def test_hologram_frame_has_avatar_on_key_background():
    renderer = HologramRenderer(170, 210)
    for i in range(10):
        frame = renderer.render(i / 30, "speaking", 0.7)
    pixels = np.array(frame)
    assert frame.size == (170, 210)
    background = (pixels == KEY).all(-1)
    assert 0.4 < background.mean() < 0.95


def test_desktop_avatar_follows_hud_visibility(bus):
    avatar = DesktopAvatar(bus, on_talk=lambda: None, on_open=lambda: None)
    bus.publish("visibility", visible=False)
    assert avatar.wanted
    bus.publish("state", state="speaking")
    bus.publish("level", source="voice", value=0.8)
    assert avatar.state == "speaking" and avatar.level == 0.8
    bus.publish("visibility", visible=True)
    assert not avatar.wanted
