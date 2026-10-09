from __future__ import annotations

import json
import os
import re
import threading
from typing import Dict, Optional

from ..config import DATA_DIR
from ..plan import Plan
from . import Skill


class KnowledgeSkill(Skill):
    name = "knowledge"
    description = "Remember, recall and forget facts about the user"

    _REMEMBER = re.compile(r"^(?:please )?remember(?: that)? (?:my )?(.+?) (?:is|are) (.+?)[.!]*$")
    _NAME = re.compile(r"^(?:my name is|call me|i am called|i'm called) ([a-z][a-z' -]{0,30}?)[.!]*$")
    _RECALL = re.compile(r"^(?:what(?:'s| is| are) my|do you (?:know|remember) my|recall my|tell me my) (.+?)[?.!]*$")
    _FORGET = re.compile(r"^(?:please )?forget (?:about )?(?:my )?(.+?)[.!]*$")
    _WHOAMI = re.compile(r"^(?:what(?:'s| is) my name|who am i|do you know (?:me|my name))[?.!]*$")
    _LIST = re.compile(r"^what do you (?:know|remember) about me[?.!]*$")

    def __init__(self, ctx, path: Optional[str] = None):
        super().__init__(ctx)
        self.path = path or os.path.join(DATA_DIR, "knowledge.json")
        self._lock = threading.Lock()
        self.facts: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {str(k): str(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError, AttributeError):
            return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2)
        os.replace(tmp, self.path)

    def remember(self, key: str, value: str) -> None:
        with self._lock:
            self.facts[key.strip().lower()] = value.strip()
            self._save()

    @property
    def user_name(self) -> str:
        return self.facts.get("name", "")

    def can_handle(self, text: str) -> bool:
        return any(p.match(text) for p in (self._REMEMBER, self._NAME, self._RECALL, self._FORGET,
                                            self._WHOAMI, self._LIST))

    def handle(self, text: str) -> Optional[Plan]:
        if m := self._NAME.match(text):
            name = m.group(1).strip().title()
            self.remember("name", name)
            return Plan.say(f"Noted. I'll call you {name} from now on.")
        if self._WHOAMI.match(text):
            if self.user_name:
                return Plan.say(f"You're {self.user_name}. I'd recognise that voice anywhere.")
            return Plan.say("You haven't told me your name yet. Say 'my name is', followed by your name.",
                            expect_reply=True)
        if self._LIST.match(text):
            if not self.facts:
                return Plan.say("Nothing yet. You're a person of mystery.")
            items = [f"your {k} is {v}" for k, v in self.facts.items()]
            return Plan.say("I know that " + "; ".join(items) + ".")
        if m := self._REMEMBER.match(text):
            key, value = m.group(1), m.group(2)
            if key in {"name", "my name"}:
                key = "name"
                value = value.title()
            self.remember(key, value)
            return Plan.say(f"Committed to memory: your {key} is {value}.")
        if m := self._RECALL.match(text):
            return self._recall(m.group(1))
        if m := self._FORGET.match(text):
            return self._forget(m.group(1))
        return None

    def _find(self, query: str) -> Optional[str]:
        query = query.strip().lower()
        if query in self.facts:
            return query
        for key in self.facts:
            if key in query or query in key:
                return key
        return None

    def _recall(self, query: str) -> Plan:
        key = self._find(query)
        if key:
            return Plan.say(f"Your {key} is {self.facts[key]}.")
        return Plan.say(f"I don't know your {query} yet. Tell me to remember it.")

    def _forget(self, query: str) -> Plan:
        if query in {"everything", "it all", "all of it"}:
            with self._lock:
                self.facts.clear()
                self._save()
            return Plan.say("Memory banks purged.")
        key = self._find(query)
        if not key:
            return Plan.say(f"I had nothing stored about your {query}.")
        with self._lock:
            del self.facts[key]
            self._save()
        return Plan.say(f"Done. Your {key} has been forgotten.")

    def context(self) -> str:
        if not self.facts:
            return ""
        return "Known facts about the user: " + "; ".join(f"{k}: {v}" for k, v in self.facts.items())
