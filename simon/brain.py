from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .commands import CustomCommands
from .config import Settings
from .events import EventBus
from .intents import IntentMatcher
from .memory import Memory
from .plan import ACTIONS, POWER_ACTIONS, Action, Plan
from .skills import SkillContext, SkillManager

log = logging.getLogger(__name__)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(ACTIONS)},
                    "target": {"type": ["string", "null"]},
                },
                "required": ["action"],
            },
        },
    },
    "required": ["response", "actions"],
}

_YES = re.compile(r"^(?:yes|yeah|yep|confirm(?:ed)?|do it|go ahead|affirmative|proceed|sure|ok(?:ay)?)\b")
_NO = re.compile(r"^(?:no|nope|negative|cancel|abort|stop|don't|do not|never ?mind)\b")


class Brain:
    def __init__(self, settings: Settings, bus: EventBus, say):
        self.settings = settings
        self.bus = bus
        self.memory = Memory(max_messages=30)
        self.commands = CustomCommands()
        self.skills = SkillManager(SkillContext(settings, bus, say))
        self.intents = IntentMatcher(name=settings.get("assistant.name", "Simon"))
        self._pending: Optional[Plan] = None
        self._client = None
        self.llm_online = False

    @property
    def model(self) -> str:
        return self.settings.get("llm.model", "llama3.2")

    def start(self) -> None:
        self.skills.start()
        threading.Thread(target=self._probe_llm, name="llm-probe", daemon=True).start()

    def think(self, text: str) -> Plan:
        text = text.strip()
        if not text:
            return Plan.say("I'm listening.", expect_reply=True)

        plan = self._resolve_pending(text) or self._route(text)
        if plan.meta.get("clear_memory"):
            self.memory.clear()
        needs_confirm = any(a.name in POWER_ACTIONS for a in plan.actions) and not plan.meta.get("confirmed")
        if needs_confirm and self.settings.get("safety.confirm_power_actions"):
            plan = self._ask_confirmation(plan)

        self.memory.add_user(text)
        self.memory.add_assistant(plan.response)
        return plan

    def _route(self, text: str) -> Plan:
        custom = self.commands.match(text)
        if custom:
            actions = [a for a in (Action.from_dict(d) for d in custom["actions"]) if a]
            return Plan(custom.get("response") or f"Running {custom['name']}.", actions, source="command")
        for stage in (self.intents.match, self.skills.handle):
            plan = stage(text)
            if plan:
                return plan
        return self._ask_llm(text)

    def _ask_confirmation(self, plan: Plan) -> Plan:
        self._pending = plan
        verb = next(a.name for a in plan.actions if a.name in POWER_ACTIONS)
        noun = {"shutdown": "shut down", "restart": "restart", "sleep": "put the system to sleep"}[verb]
        return Plan.say(f"You want me to {noun}? Please confirm.", expect_reply=True, meta={"confirm": verb})

    def _resolve_pending(self, text: str) -> Optional[Plan]:
        pending, self._pending = self._pending, None
        if pending is None:
            return None
        if _YES.match(text.lower()):
            delay = int(self.settings.get("safety.power_delay", 10))
            name = pending.actions[0].name
            pending.actions = [Action(name, str(delay))]
            pending.response = {
                "shutdown": f"Shutdown sequence initiated. T-minus {delay} seconds. Say abort to cancel.",
                "restart": f"Restarting in {delay} seconds. Say abort to cancel.",
                "sleep": "Going dark. Goodnight.",
            }[name]
            pending.meta = {"confirmed": True}
            return pending
        if _NO.match(text.lower()):
            return Plan.say("Cancelled. Standing down.")
        return None

    def _connect(self):
        if self._client is None:
            import ollama

            host = self.settings.get("llm.host") or None
            self._client = ollama.Client(host=host, timeout=self.settings.get("llm.timeout", 30))
        return self._client

    def _probe_llm(self) -> None:
        if not self.settings.get("llm.enabled", True):
            self.bus.publish("status", llm="disabled", model=self.model)
            return
        try:
            self._connect().list()
            self.llm_online = True
        except Exception as exc:
            log.warning("Ollama unreachable (%s) — running on local intents only", exc)
            self.llm_online = False
        self.bus.publish("status", llm="online" if self.llm_online else "offline", model=self.model)

    def _system_prompt(self) -> str:
        name = self.settings.get("assistant.name", "Simon")
        user = self.skills.get("knowledge")
        user_name = getattr(user, "user_name", "") or self.settings.get("assistant.user_name", "")
        actions = "\n".join(f"- {k}: {v}" for k, v in ACTIONS.items())
        now = datetime.now()
        return (
            f"You are {name}, an advanced AI assistant running on the user's Windows PC, in the spirit of "
            f"JARVIS. {self.settings.get('assistant.personality', '')}\n"
            f"{'The user is called ' + user_name + '.' if user_name else ''}\n"
            f"It is {now:%A %d %B %Y}, {now:%H:%M}.\n\n"
            "Reply ONLY with JSON: {\"response\": str, \"actions\": [{\"action\": str, \"target\": str|null}]}.\n"
            "`response` is spoken aloud: one to three natural sentences, no markdown, no lists, no emoji.\n"
            "`actions` is usually empty; add entries only when the user wants something done.\n"
            f"Available actions:\n{actions}\n\n"
            f"{self.skills.context()}"
        ).strip()

    def _ask_llm(self, text: str) -> Plan:
        if not self.settings.get("llm.enabled", True):
            return Plan.say("That's beyond my local command set, and my language core is disabled.", source="fallback")
        messages: List[Dict[str, str]] = [{"role": "system", "content": self._system_prompt()}]
        messages += self.memory.context()
        messages.append({"role": "user", "content": text})
        try:
            reply = self._connect().chat(
                model=self.model,
                messages=messages,
                format=RESPONSE_SCHEMA,
                options={"temperature": self.settings.get("llm.temperature", 0.4)},
            )
            content = reply["message"]["content"]
            if not self.llm_online:
                self.llm_online = True
                self.bus.publish("status", llm="online", model=self.model)
        except Exception as exc:
            log.warning("LLM request failed: %s", exc)
            if self.llm_online:
                self.llm_online = False
                self.bus.publish("status", llm="offline", model=self.model)
            return Plan.say(
                "My language core is offline. Make sure Ollama is running. Direct commands still work.",
                source="fallback",
            )
        plan = parse_llm_reply(content)
        plan.source = "llm"
        return plan


def _first_json_object(content: str) -> Optional[str]:
    start = content.find("{")
    if start < 0:
        return None
    depth, in_str, escape = 0, False, False
    for i, ch in enumerate(content[start:], start):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return content[start:i + 1]
    return None


def parse_llm_reply(content: str) -> Plan:
    raw = _first_json_object(content or "")
    data: Dict[str, Any] = {}
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
    if not isinstance(data, dict) or not data:
        text = (content or "").split("{")[0].strip() or "Done."
        return Plan.say(text)

    items = data.get("actions")
    if items is None and "action" in data:
        items = [data]
    actions = []
    for item in items or []:
        if isinstance(item, dict):
            action = Action.from_dict(item)
            if action and action.name in ACTIONS:
                actions.append(action)
    response = str(data.get("response") or "Done.").strip()
    return Plan(response, actions, expect_reply=response.endswith("?"))
