from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any, Dict

log = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
DATA_DIR = os.path.join(ROOT_DIR, "data")
HUD_DIR = os.path.join(ROOT_DIR, "hud")
VOICES_DIR = os.path.join(ROOT_DIR, "voices")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS: Dict[str, Any] = {
    "assistant": {
        "name": "Simon",
        "user_name": "",
        "personality": (
            "Dry British wit, unflappable, impeccably polite. Address the user as "
            "'sir' unless told otherwise. Keep replies short enough to be spoken."
        ),
    },
    "llm": {
        "enabled": True,
        "model": "llama3.2",
        "host": "",
        "temperature": 0.4,
        "timeout": 30,
    },
    "voice": {
        "engine": "auto",
        "edge_voice": "en-GB-RyanNeural",
        "rate": "+4%",
        "pitch": "-2Hz",
        "piper_model": "jarvis.onnx",
    },
    "listening": {
        "wake_words": ["hey simon", "simon", "hey saimon", "saimon", "okay simon"],
        "wake_word_enabled": True,
        "hotkey": "ctrl+space",
        "conversation_window": 6.0,
        "command_timeout": 6,
        "phrase_limit": 12,
        "language": "en-GB",
    },
    "hud": {
        "host": "127.0.0.1",
        "port": 47800,
        "width": 1440,
        "height": 860,
        "fullscreen": False,
        "always_on_top": True,
        "auto_hide": True,
        "auto_hide_delay": 8.0,
        "sound_effects": True,
        "accent": "#00e5ff",
    },
    "weather": {"location": "London", "units": "metric"},
    "safety": {"confirm_power_actions": True, "power_delay": 10},
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    def __init__(self, data: Dict[str, Any], path: str | None = None):
        self._data = data
        self.path = path

    @classmethod
    def load(cls, path: str = SETTINGS_PATH) -> "Settings":
        user: Dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    user = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("Could not read %s (%s) — using defaults", path, exc)
        return cls(_deep_merge(DEFAULTS, user), path)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def as_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def public(self) -> Dict[str, Any]:
        return {
            "name": self.get("assistant.name"),
            "user": self.get("assistant.user_name"),
            "model": self.get("llm.model"),
            "voice": self.get("voice.edge_voice"),
            "hotkey": self.get("listening.hotkey"),
            "wake_word": (self.get("listening.wake_words") or ["simon"])[0],
            "location": self.get("weather.location"),
            "sound_effects": self.get("hud.sound_effects"),
            "accent": self.get("hud.accent"),
        }
