from __future__ import annotations

import itertools
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..plan import Plan
from . import Skill

_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
    "fifty": 50, "sixty": 60, "ninety": 90,
}
_UNITS = {"h": 3600, "hr": 3600, "hour": 3600, "m": 60, "min": 60, "minute": 60, "s": 1, "sec": 1, "second": 1}
_DURATION_RE = re.compile(
    r"(\d+(?:\.\d+)?|" + "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True)) + r")"
    r"\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b"
)


def parse_duration(text: str) -> Optional[int]:
    text = text.lower().replace("half an hour", "30 minutes").replace("half a minute", "30 seconds")
    text = text.replace("quarter of an hour", "15 minutes").replace("an hour and a half", "90 minutes")
    total = 0.0
    for amount, unit in _DURATION_RE.findall(text):
        value = float(amount) if amount[0].isdigit() else _WORD_NUMBERS[amount]
        unit = unit.rstrip("s") or "s"
        total += value * _UNITS.get(unit, _UNITS.get(unit[:3], _UNITS.get(unit[0], 1)))
    return int(total) if total > 0 else None


def humanize(seconds: int) -> str:
    seconds = int(seconds)
    parts = []
    for label, size in (("hour", 3600), ("minute", 60), ("second", 1)):
        value, seconds = divmod(seconds, size)
        if value:
            parts.append(f"{value} {label}{'s' if value != 1 else ''}")
    if not parts:
        return "0 seconds"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


@dataclass
class Timer:
    id: int
    label: str
    duration: int
    ends_at: float
    is_reminder: bool = False
    _timer: Optional[threading.Timer] = field(default=None, repr=False)

    def remaining(self) -> float:
        return max(0.0, self.ends_at - time.time())

    def public(self) -> Dict:
        return {"id": self.id, "label": self.label, "duration": self.duration,
                "ends_at": self.ends_at, "reminder": self.is_reminder}


class TimerSkill(Skill):
    name = "timer"
    description = "Timers, countdowns and reminders"

    _TRIGGER = re.compile(r"\b(timer|countdown|remind me|reminder|alarm|wake me)\b")

    def __init__(self, ctx):
        super().__init__(ctx)
        self._timers: Dict[int, Timer] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def can_handle(self, text: str) -> bool:
        return bool(self._TRIGGER.search(text))

    def handle(self, text: str) -> Optional[Plan]:
        if re.search(r"\b(cancel|stop|clear|delete|kill)\b", text):
            return self._cancel_all()
        if re.search(r"\b(how (much|long)|time left|remaining|status|check)\b", text):
            return self._status()

        duration = parse_duration(text)
        if duration is None:
            return Plan.say("For how long? Try 'set a timer for five minutes'.", expect_reply=True)

        reminder = None
        m = re.search(r"\b(?:to|that|about)\s+(.+?)(?:\s+in\s+\d.*)?$", text)
        if "remind" in text and m:
            reminder = m.group(1).strip(" .")
            reminder = re.sub(r"\bmy\b", "your", reminder)
        label = reminder or f"{humanize(duration)} timer"
        self.start_timer(duration, label, is_reminder=bool(reminder))

        if reminder:
            return Plan.say(f"I'll remind you to {reminder} in {humanize(duration)}.")
        return Plan.say(f"Timer set. {humanize(duration).capitalize()}, starting now.")

    def start_timer(self, duration: int, label: str, is_reminder: bool = False) -> Timer:
        timer = Timer(next(self._ids), label, duration, time.time() + duration, is_reminder)
        timer._timer = threading.Timer(duration, self._fire, args=(timer.id,))
        timer._timer.daemon = True
        with self._lock:
            self._timers[timer.id] = timer
        timer._timer.start()
        self._publish()
        return timer

    def _fire(self, timer_id: int) -> None:
        with self._lock:
            timer = self._timers.pop(timer_id, None)
        if not timer:
            return
        self._publish()
        if timer.is_reminder:
            message = f"Reminder: {timer.label}."
        else:
            message = f"Your {timer.label} is complete."
        self.ctx.bus.publish("notify", level="alert", title="TIMER COMPLETE" if not timer.is_reminder else "REMINDER",
                             text=message)
        self.ctx.say(message)

    def _cancel_all(self) -> Plan:
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
        for t in timers:
            if t._timer:
                t._timer.cancel()
        self._publish()
        if not timers:
            return Plan.say("There are no active timers.")
        return Plan.say(f"Cancelled {len(timers)} timer{'s' if len(timers) != 1 else ''}.")

    def _status(self) -> Plan:
        timers = self.active()
        if not timers:
            return Plan.say("No timers running.")
        lines = [f"{t.label}: {humanize(round(t.remaining()))} left" for t in timers]
        return Plan.say(". ".join(lines) + ".")

    def active(self) -> List[Timer]:
        with self._lock:
            return sorted(self._timers.values(), key=lambda t: t.ends_at)

    def _publish(self) -> None:
        self.ctx.bus.publish("timers", timers=[t.public() for t in self.active()])

    def context(self) -> str:
        timers = self.active()
        if not timers:
            return ""
        return "Active timers: " + "; ".join(f"{t.label} ({humanize(round(t.remaining()))} left)" for t in timers)
