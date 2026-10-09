from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..config import Settings
from ..events import EventBus
from ..plan import Plan

log = logging.getLogger(__name__)


@dataclass
class SkillContext:
    settings: Settings
    bus: EventBus
    say: Callable[[str], None]


class Skill(ABC):
    name = "skill"
    description = ""

    def __init__(self, ctx: SkillContext):
        self.ctx = ctx

    @abstractmethod
    def can_handle(self, text: str) -> bool: ...

    @abstractmethod
    def handle(self, text: str) -> Optional[Plan]: ...

    def context(self) -> str:
        return ""

    def start(self) -> None:
        pass


class SkillManager:
    def __init__(self, ctx: SkillContext):
        from .files import FileSkill
        from .knowledge import KnowledgeSkill
        from .system import SystemSkill
        from .timer import TimerSkill
        from .weather import WeatherSkill

        self.skills: List[Skill] = [
            TimerSkill(ctx),
            KnowledgeSkill(ctx),
            WeatherSkill(ctx),
            SystemSkill(ctx),
            FileSkill(ctx),
        ]

    def get(self, name: str) -> Optional[Skill]:
        return next((s for s in self.skills if s.name == name), None)

    def handle(self, text: str) -> Optional[Plan]:
        lowered = text.lower().strip()
        for skill in self.skills:
            try:
                if skill.can_handle(lowered):
                    plan = skill.handle(lowered)
                    if plan is not None:
                        plan.source = f"skill:{skill.name}"
                        return plan
            except Exception:
                log.exception("Skill %s failed", skill.name)
                return Plan.say(f"My {skill.name} module hit a snag. I've logged the details.")
        return None

    def context(self) -> str:
        parts = []
        for skill in self.skills:
            try:
                ctx = skill.context()
            except Exception:
                ctx = ""
            if ctx:
                parts.append(ctx)
        return "\n".join(parts)

    def start(self) -> None:
        for skill in self.skills:
            try:
                skill.start()
            except Exception:
                log.exception("Could not start skill %s", skill.name)
