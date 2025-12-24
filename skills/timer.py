"""
Timer and reminder skill with background execution.
"""

import threading
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from . import Skill


class TimerSkill(Skill):
    """Manage timers and reminders."""
    
    name = "timer"
    description = "Set timers, alarms, and reminders"
    triggers = ["timer", "remind", "reminder", "alarm", "wake me", "minutes", "seconds", "hours"]
    
    def __init__(self, assistant=None):
        super().__init__(assistant)
        self.active_timers: List[Dict] = []
        self._speaker = None
    
    def can_handle(self, command: str) -> bool:
        return any(trigger in command for trigger in self.triggers)
    
    def execute(self, command: str) -> Dict[str, Any]:
        # Parse duration from command
        duration = self._parse_duration(command)
        
        if duration is None:
            return {
                "action": "speak",
                "target": None,
                "response": "Sorry, I couldn't understand the duration. Try 'set a timer for 5 minutes'."
            }
        
        # Extract reminder message if any
        message = self._extract_message(command)
        
        # Start timer in background
        timer_id = len(self.active_timers)
        self._start_timer(duration, message, timer_id)
        
        # Format response
        if duration < 60:
            time_str = f"{duration} seconds"
        elif duration < 3600:
            mins = duration // 60
            time_str = f"{mins} minute{'s' if mins > 1 else ''}"
        else:
            hours = duration // 3600
            time_str = f"{hours} hour{'s' if hours > 1 else ''}"
        
        return {
            "action": "speak",
            "target": None,
            "response": f"Timer set for {time_str}."
        }
    
    def _parse_duration(self, command: str) -> Optional[int]:
        """Parse duration in seconds from command."""
        command = command.lower()
        
        # Pattern: X hours/minutes/seconds
        patterns = [
            (r"(\d+)\s*hours?", 3600),
            (r"(\d+)\s*minutes?", 60),
            (r"(\d+)\s*seconds?", 1),
            (r"(\d+)\s*mins?", 60),
            (r"(\d+)\s*secs?", 1),
        ]
        
        total = 0
        for pattern, multiplier in patterns:
            match = re.search(pattern, command)
            if match:
                total += int(match.group(1)) * multiplier
        
        return total if total > 0 else None
    
    def _extract_message(self, command: str) -> str:
        """Extract reminder message from command."""
        patterns = ["to ", "that ", "about "]
        for pattern in patterns:
            if pattern in command.lower():
                parts = command.lower().split(pattern, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return "Timer complete!"
    
    def _start_timer(self, duration: int, message: str, timer_id: int) -> None:
        """Start a background timer."""
        timer_info = {
            "id": timer_id,
            "duration": duration,
            "message": message,
            "end_time": datetime.now() + timedelta(seconds=duration),
            "active": True
        }
        self.active_timers.append(timer_info)
        
        def timer_callback():
            time.sleep(duration)
            if timer_info["active"]:
                self._on_timer_complete(timer_info)
        
        thread = threading.Thread(target=timer_callback, daemon=True)
        thread.start()
    
    def _on_timer_complete(self, timer_info: Dict) -> None:
        """Called when timer completes."""
        timer_info["active"] = False
        message = timer_info["message"]
        
        # Try to speak using pygame for notification sound
        try:
            import pygame
            pygame.mixer.init()
            # Beep notification (generate simple tone)
            print(f"\n[Timer] {message}")
            
            # Use assistant's speaker if available
            if self.assistant and hasattr(self.assistant, 'speaker'):
                self.assistant.speaker.speak(message)
        except Exception as e:
            print(f"[Timer] Complete: {message}")
    
    def get_context(self) -> str:
        """Return active timers for LLM context."""
        active = [t for t in self.active_timers if t["active"]]
        if not active:
            return ""
        
        lines = ["Active timers:"]
        for t in active:
            remaining = (t["end_time"] - datetime.now()).total_seconds()
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                lines.append(f"  - {mins}m {secs}s remaining: {t['message']}")
        
        return "\n".join(lines)
