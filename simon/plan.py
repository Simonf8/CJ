from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ACTIONS: Dict[str, str] = {
    "open_app": "Launch an application. target = app name (chrome, spotify, vscode …)",
    "open_file": "Open a file or folder. target = path or a known folder (downloads, documents, desktop)",
    "open_url": "Open a website. target = URL",
    "search_google": "Web search. target = query",
    "search_youtube": "YouTube search. target = query",
    "volume_up": "Raise system volume",
    "volume_down": "Lower system volume",
    "volume_mute": "Toggle mute",
    "volume_set": "Set volume. target = 0-100",
    "media_play_pause": "Play / pause media",
    "media_next": "Next track",
    "media_prev": "Previous track",
    "lock_screen": "Lock the workstation",
    "screenshot": "Capture the screen",
    "shutdown": "Power off the computer (asks for confirmation)",
    "restart": "Restart the computer (asks for confirmation)",
    "sleep": "Put the computer to sleep (asks for confirmation)",
    "cancel_shutdown": "Abort a pending shutdown or restart",
    "hud_hide": "Dismiss the HUD / go to standby",
}

POWER_ACTIONS = {"shutdown", "restart", "sleep"}


@dataclass
class Action:
    name: str
    target: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Action"]:
        name = str(data.get("action") or data.get("name") or "").strip()
        if not name or name == "speak":
            return None
        target = data.get("target")
        if target is not None and not isinstance(target, str):
            target = str(target)
        if isinstance(target, str) and target.strip().lower() in {"", "null", "none"}:
            target = None
        return cls(name, target)

    def as_dict(self) -> Dict[str, Any]:
        return {"action": self.name, "target": self.target}


@dataclass
class Plan:
    response: str
    actions: List[Action] = field(default_factory=list)
    source: str = "intent"
    expect_reply: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def say(cls, text: str, **kwargs: Any) -> "Plan":
        return cls(response=text, **kwargs)

    @classmethod
    def do(cls, text: str, name: str, target: Optional[str] = None, **kwargs: Any) -> "Plan":
        return cls(response=text, actions=[Action(name, target)], **kwargs)
