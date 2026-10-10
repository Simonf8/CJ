from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from ..plan import Plan
from . import Skill

log = logging.getLogger(__name__)

REFRESH_SECONDS = 20 * 60


def fetch_weather(location: str, timeout: float = 8.0) -> Dict[str, Any]:
    url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "Simon-Assistant/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data["current_condition"][0]
    area = data.get("nearest_area", [{}])[0]
    today = data.get("weather", [{}])[0]
    hourly = today.get("hourly", [])
    rain = max((int(h.get("chanceofrain", 0)) for h in hourly), default=0)
    return {
        "location": area.get("areaName", [{"value": location}])[0]["value"],
        "country": area.get("country", [{"value": ""}])[0]["value"],
        "temp_c": int(current["temp_C"]),
        "temp_f": int(current["temp_F"]),
        "feels_c": int(current.get("FeelsLikeC", current["temp_C"])),
        "feels_f": int(current.get("FeelsLikeF", current["temp_F"])),
        "description": current["weatherDesc"][0]["value"].strip(),
        "humidity": int(current["humidity"]),
        "wind_kph": int(current.get("windspeedKmph", 0)),
        "wind_dir": current.get("winddir16Point", ""),
        "high_c": int(today.get("maxtempC", current["temp_C"])),
        "low_c": int(today.get("mintempC", current["temp_C"])),
        "high_f": int(today.get("maxtempF", current["temp_F"])),
        "low_f": int(today.get("mintempF", current["temp_F"])),
        "rain_chance": rain,
        "code": int(current.get("weatherCode", 113)),
        "fetched_at": time.time(),
    }


class WeatherSkill(Skill):
    name = "weather"
    description = "Current conditions and today's forecast"

    _TRIGGER = re.compile(r"\b(weather|forecast|temperature outside|how (?:hot|cold|warm) is it|is it (?:going to )?(?:rain|snow)|will it (?:rain|snow)|need an umbrella|need a jacket)\b")
    _LOCATION = re.compile(r"\b(?:in|for|at|around)\s+([a-z][a-z .'-]+?)(?:\s+(?:today|tomorrow|right now|now|this week))?[?.!]*$")

    def __init__(self, ctx):
        super().__init__(ctx)
        self._cache: Optional[Dict[str, Any]] = None
        self._stop = threading.Event()

    @property
    def home(self) -> str:
        return self.ctx.settings.get("weather.location", "London")

    @property
    def metric(self) -> bool:
        return self.ctx.settings.get("weather.units", "metric") != "imperial"

    def can_handle(self, text: str) -> bool:
        return bool(self._TRIGGER.search(text))

    def handle(self, text: str) -> Optional[Plan]:
        m = self._LOCATION.search(text)
        location = m.group(1).strip() if m else self.home
        try:
            w = fetch_weather(location)
        except Exception as exc:
            log.warning("Weather lookup failed: %s", exc)
            return Plan.say("I can't reach the weather service at the moment.")
        if location == self.home:
            self._cache = w
            self.ctx.bus.publish("weather", **w)
        return Plan.say(self.describe(w, rain_question=bool(re.search(r"rain|umbrella", text))))

    def describe(self, w: Dict[str, Any], rain_question: bool = False) -> str:
        u = "c" if self.metric else "f"
        deg = "degrees"
        place = w["location"]
        if rain_question:
            chance = w["rain_chance"]
            verdict = "Take an umbrella." if chance >= 50 else "You should stay dry."
            return f"There's a {chance} percent chance of rain in {place} today. {verdict}"
        return (f"It's {w[f'temp_{u}']} {deg} in {place} and {w['description'].lower()}, "
                f"feeling like {w[f'feels_{u}']}. Today's high is {w[f'high_{u}']}, low {w[f'low_{u}']}, "
                f"with a {w['rain_chance']} percent chance of rain.")

    def start(self) -> None:
        threading.Thread(target=self._loop, name="weather", daemon=True).start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._cache = fetch_weather(self.home)
                self.ctx.bus.publish("weather", **self._cache)
                wait = REFRESH_SECONDS
            except Exception as exc:
                log.debug("Weather refresh failed: %s", exc)
                wait = 120
            self._stop.wait(wait)

    def context(self) -> str:
        if not self._cache:
            return ""
        w = self._cache
        return (f"Weather in {w['location']}: {w['temp_c']}°C, {w['description']}, "
                f"{w['rain_chance']}% chance of rain today.")
