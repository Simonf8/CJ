import time

import pytest

from simon.skills.files import safe_name
from simon.skills.timer import humanize, parse_duration
from simon.speech.listener import split_wake_word


@pytest.mark.parametrize("text, seconds", [
    ("set a timer for 5 minutes", 300),
    ("timer for 1 hour and 30 minutes", 5400),
    ("countdown 45 seconds", 45),
    ("set a timer for five minutes", 300),
    ("timer for half an hour", 1800),
    ("remind me in a minute", 60),
    ("set a timer", None),
])
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


def test_humanize():
    assert humanize(3725) == "1 hour, 2 minutes and 5 seconds"
    assert humanize(60) == "1 minute"


def test_timer_skill_fires_and_publishes(brain, bus):
    events = []
    bus.on(events.append)
    timer = brain.skills.get("timer")
    timer.start_timer(0, "tea", is_reminder=True)
    time.sleep(0.2)
    assert brain.spoken == ["Reminder: tea."]
    assert any(e["type"] == "notify" for e in events)
    assert timer.active() == []


def test_timer_does_not_steal_unrelated_minutes(brain):
    assert not brain.skills.get("timer").can_handle("how many minutes are in a day")


def test_reminder_phrase(brain):
    plan = brain.think("remind me to call mom in 10 minutes")
    assert plan.response == "I'll remind you to call mom in 10 minutes."
    brain.think("cancel all timers")


def test_knowledge_roundtrip(brain):
    brain.think("remember my favourite colour is green")
    assert brain.think("what is my favourite colour").response == "Your favourite colour is green."
    brain.think("forget my favourite colour")
    assert "don't know" in brain.think("what's my favourite colour").response


def test_name_is_remembered(brain):
    brain.think("my name is tony")
    assert "Tony" in brain.think("what's my name").response
    assert "The user is called Tony" in brain._system_prompt()


@pytest.mark.parametrize("raw, ok", [
    ("notes", True), ("report dot pdf", True), ("../secrets", False),
    ("a/b", False), ("..", False), ("", False), ("con:", False),
])
def test_safe_name(raw, ok):
    assert (safe_name(raw) is not None) == ok


def test_file_skill_confined_to_base_dir(brain, tmp_path):
    files = brain.skills.get("files")
    files.base_dir = str(tmp_path)
    assert "Created notes.txt" in brain.think("create file notes").response
    assert (tmp_path / "notes.txt").exists()
    assert "valid" in brain.think("create file ../../evil").response


@pytest.mark.parametrize("heard, found, rest", [
    ("hey simon open chrome", True, "open chrome"),
    ("Simon, what time is it?", True, "what time is it"),
    ("simon", True, ""),
    ("simonetta is here", False, ""),
    ("hello there", False, ""),
])
def test_wake_word(heard, found, rest):
    assert split_wake_word(heard, ["hey simon", "simon"]) == (found, rest)
