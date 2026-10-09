from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from .config import CONFIG_DIR

log = logging.getLogger(__name__)


class CustomCommands:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(CONFIG_DIR, "commands.json")
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._mtime = 0.0
        self.reload()

    def reload(self) -> None:
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            self._commands = {}
            return
        if mtime == self._mtime:
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Ignoring invalid %s: %s", self.path, exc)
            return
        self._mtime = mtime
        self._commands = {}
        for name, spec in raw.items():
            if isinstance(spec, list):
                spec = {"actions": spec}
            self._commands[name.lower().strip()] = {
                "actions": spec.get("actions", []),
                "response": spec.get("response"),
            }

    def match(self, phrase: str) -> Optional[Dict[str, Any]]:
        self.reload()
        text = phrase.lower().strip(" .!?")
        if text in self._commands:
            return {"name": text, **self._commands[text]}
        for name in sorted(self._commands, key=len, reverse=True):
            if re.search(rf"\b{re.escape(name)}\b", text):
                return {"name": name, **self._commands[name]}
        return None

    def names(self) -> List[str]:
        return list(self._commands)
