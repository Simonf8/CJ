"""
Knowledge base skill for remembering and recalling facts.
"""

import json
import os
from typing import Dict, Any, Optional
from . import Skill


class KnowledgeSkill(Skill):
    """Remember and recall user facts."""
    
    name = "knowledge"
    description = "Remember facts and recall them later"
    triggers = ["remember", "forget", "what is my", "what's my", "do you know my", "recall"]
    
    STORAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge.json")
    
    def __init__(self, assistant=None):
        super().__init__(assistant)
        self.facts: Dict[str, str] = {}
        self._load()
    
    def _load(self) -> None:
        """Load facts from disk."""
        try:
            if os.path.exists(self.STORAGE_FILE):
                with open(self.STORAGE_FILE, "r") as f:
                    self.facts = json.load(f)
        except Exception:
            self.facts = {}
    
    def _save(self) -> None:
        """Save facts to disk."""
        os.makedirs(os.path.dirname(self.STORAGE_FILE), exist_ok=True)
        with open(self.STORAGE_FILE, "w") as f:
            json.dump(self.facts, f, indent=2)
    
    def can_handle(self, command: str) -> bool:
        return any(trigger in command for trigger in self.triggers)
    
    def execute(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower()
        
        # Remember something
        if "remember" in command_lower:
            return self._remember(command)
        
        # Forget something
        if "forget" in command_lower:
            return self._forget(command)
        
        # Recall something
        if any(t in command_lower for t in ["what is my", "what's my", "do you know my", "recall"]):
            return self._recall(command)
        
        return {
            "action": "speak",
            "target": None,
            "response": "I'm not sure what you want me to do with that information."
        }
    
    def _remember(self, command: str) -> Dict[str, Any]:
        """Parse and store a fact."""
        # Patterns: "remember my X is Y", "remember that my X is Y"
        command_lower = command.lower()
        
        # Remove "remember" and "that"
        text = command_lower.replace("remember that ", "").replace("remember ", "")
        
        # Look for "my X is Y" pattern
        if " is " in text:
            parts = text.split(" is ", 1)
            key = parts[0].replace("my ", "").strip()
            value = parts[1].strip()
            
            self.facts[key] = value
            self._save()
            
            return {
                "action": "speak",
                "target": None,
                "response": f"Got it! I'll remember that your {key} is {value}."
            }
        
        return {
            "action": "speak",
            "target": None,
            "response": "Try saying 'remember my favorite color is blue'."
        }
    
    def _forget(self, command: str) -> Dict[str, Any]:
        """Remove a fact."""
        command_lower = command.lower().replace("forget my ", "").replace("forget ", "")
        
        # Find matching key
        for key in list(self.facts.keys()):
            if key in command_lower or command_lower in key:
                del self.facts[key]
                self._save()
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Done, I've forgotten your {key}."
                }
        
        return {
            "action": "speak",
            "target": None,
            "response": "I don't have that information stored."
        }
    
    def _recall(self, command: str) -> Dict[str, Any]:
        """Recall a stored fact."""
        command_lower = command.lower()
        
        # Extract what they're asking about
        for pattern in ["what is my ", "what's my ", "do you know my ", "recall my ", "recall "]:
            if pattern in command_lower:
                query = command_lower.split(pattern)[1].strip().rstrip("?")
                break
        else:
            query = ""
        
        # Find matching fact
        for key, value in self.facts.items():
            if key in query or query in key:
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Your {key} is {value}."
                }
        
        return {
            "action": "speak",
            "target": None,
            "response": f"I don't know your {query}. Tell me to remember it!"
        }
    
    def get_context(self) -> str:
        """Return all known facts for LLM context."""
        if not self.facts:
            return ""
        
        lines = ["Known facts about the user:"]
        for key, value in self.facts.items():
            lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines)
