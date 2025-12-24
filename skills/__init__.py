"""
Skills plugin system for Simon assistant.
Extensible architecture for adding new capabilities.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import importlib
import os


class Skill(ABC):
    """Base class for all skills."""
    
    # Skill metadata
    name: str = "base_skill"
    description: str = "Base skill class"
    triggers: List[str] = []  # Keywords that activate this skill
    
    def __init__(self, assistant=None):
        self.assistant = assistant
    
    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Check if this skill can handle the command."""
        pass
    
    @abstractmethod
    def execute(self, command: str) -> Dict[str, Any]:
        """Execute the skill and return action dict."""
        pass
    
    def get_context(self) -> str:
        """Return context string for LLM (optional)."""
        return ""


class SkillManager:
    """Manages loading and dispatching skills."""
    
    def __init__(self):
        self.skills: List[Skill] = []
        self._load_builtin_skills()
    
    def _load_builtin_skills(self) -> None:
        """Load all built-in skills."""
        from .weather import WeatherSkill
        from .timer import TimerSkill
        from .knowledge import KnowledgeSkill
        from .files import FileSkill
        
        self.register(WeatherSkill())
        self.register(TimerSkill())
        self.register(KnowledgeSkill())
        self.register(FileSkill())
    
    def register(self, skill: Skill) -> None:
        """Register a new skill."""
        self.skills.append(skill)
        print(f"[Skills] Registered: {skill.name}")
    
    def find_skill(self, command: str) -> Optional[Skill]:
        """Find a skill that can handle the command."""
        command_lower = command.lower()
        for skill in self.skills:
            if skill.can_handle(command_lower):
                return skill
        return None
    
    def execute(self, command: str) -> Optional[Dict[str, Any]]:
        """Find and execute appropriate skill."""
        skill = self.find_skill(command)
        if skill:
            return skill.execute(command)
        return None
    
    def get_all_context(self) -> str:
        """Get combined context from all skills."""
        contexts = []
        for skill in self.skills:
            ctx = skill.get_context()
            if ctx:
                contexts.append(ctx)
        return "\n".join(contexts)
    
    def list_skills(self) -> List[Dict[str, str]]:
        """List all registered skills."""
        return [
            {"name": s.name, "description": s.description}
            for s in self.skills
        ]
