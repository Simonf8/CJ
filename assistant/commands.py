"""
Custom commands module.
Loads and executes user-defined command shortcuts.
"""

import json
import os
from typing import Optional, List, Dict


class CustomCommands:
    """Handles custom command shortcuts from config file."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "commands.json")
        
        self.config_path = config_path
        self.commands: Dict[str, List[Dict]] = {}
        self._load_commands()
    
    def _load_commands(self) -> None:
        """Load commands from config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.commands = json.load(f)
        except Exception:
            self.commands = {}
    
    def reload(self) -> None:
        """Reload commands from config file."""
        self._load_commands()
    
    def get_command(self, phrase: str) -> Optional[List[Dict]]:
        """
        Check if a phrase matches a custom command.
        
        Args:
            phrase: User's spoken phrase (lowercase)
            
        Returns:
            List of actions if match found, None otherwise
        """
        phrase_lower = phrase.lower().strip()
        
        # Exact match
        if phrase_lower in self.commands:
            return self.commands[phrase_lower]
        
        # Partial match (phrase contains command)
        for cmd_name, actions in self.commands.items():
            if cmd_name in phrase_lower:
                return actions
        
        return None
    
    def list_commands(self) -> List[str]:
        """Return list of available custom commands."""
        return list(self.commands.keys())
    
    def add_command(self, name: str, actions: List[Dict]) -> bool:
        """Add a new custom command and save to config."""
        try:
            self.commands[name.lower()] = actions
            self._save_commands()
            return True
        except Exception:
            return False
    
    def remove_command(self, name: str) -> bool:
        """Remove a custom command and save to config."""
        try:
            if name.lower() in self.commands:
                del self.commands[name.lower()]
                self._save_commands()
                return True
            return False
        except Exception:
            return False
    
    def _save_commands(self) -> None:
        """Save commands to config file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.commands, f, indent=2)
