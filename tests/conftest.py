import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simon.brain import Brain  # noqa: E402
from simon.config import Settings  # noqa: E402
from simon.events import EventBus  # noqa: E402


@pytest.fixture
def settings():
    s = Settings.load(path="/nonexistent")
    s.set("llm.enabled", False)
    return s


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def brain(settings, bus, tmp_path, monkeypatch):
    monkeypatch.setattr("simon.skills.knowledge.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("simon.skills.weather.WeatherSkill.start", lambda self: None)
    spoken = []
    b = Brain(settings, bus, say=spoken.append)
    b.spoken = spoken
    return b
