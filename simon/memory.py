from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class Memory:
    def __init__(self, max_messages: int = 30):
        self._messages: Deque[Message] = deque(maxlen=max_messages)

    def add_user(self, content: str) -> None:
        self._messages.append(Message("user", content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(Message("assistant", content))

    def context(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
