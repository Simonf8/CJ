"""
Conversation memory module.
Stores chat history for context in LLM calls.
"""

from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class Memory:
    """Stores conversation history for context."""
    
    def __init__(self, max_messages: int = 10):
        """
        Initialize memory.
        
        Args:
            max_messages: Maximum number of messages to keep.
        """
        self.max_messages = max_messages
        self.messages: List[Message] = []
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to memory."""
        self._add_message("user", content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to memory."""
        self._add_message("assistant", content)
    
    def _add_message(self, role: str, content: str) -> None:
        """Add a message and trim if needed."""
        self.messages.append(Message(
            role=role,
            content=content,
            timestamp=datetime.now()
        ))
        
        # Keep only the last N messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_context(self) -> List[Dict[str, str]]:
        """Get messages formatted for LLM context."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def get_last_user_message(self) -> str:
        """Get the last thing the user said."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return ""
    
    def clear(self) -> None:
        """Clear all memory."""
        self.messages = []
    
    def get_summary(self) -> str:
        """Get a brief summary of recent conversation."""
        if not self.messages:
            return "No recent conversation."
        
        recent = self.messages[-3:]
        lines = []
        for msg in recent:
            prefix = "User" if msg.role == "user" else "CJ"
            lines.append(f"{prefix}: {msg.content[:50]}...")
        return "\n".join(lines)
