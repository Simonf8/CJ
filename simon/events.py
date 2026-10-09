from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List

log = logging.getLogger(__name__)

Event = Dict[str, Any]

_STICKY = {"state", "config", "telemetry", "timers", "weather", "status"}
_HISTORY = {"transcript", "notify"}
_MERGED = {"status"}


class EventBus:
    def __init__(self, history: int = 60):
        self._lock = threading.Lock()
        self._queues: List[queue.Queue] = []
        self._callbacks: List[Callable[[Event], None]] = []
        self._sticky: Dict[str, Event] = {}
        self._history: Deque[Event] = deque(maxlen=history)

    def publish(self, type_: str, **payload: Any) -> Event:
        event: Event = {"type": type_, "ts": time.time(), **payload}
        with self._lock:
            if type_ in _MERGED and type_ in self._sticky:
                self._sticky[type_] = {**self._sticky[type_], **event}
            elif type_ in _STICKY:
                self._sticky[type_] = event
            if type_ in _HISTORY:
                self._history.append(event)
            queues = list(self._queues)
            callbacks = list(self._callbacks)
        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                log.exception("Event callback failed for %s", type_)
        return event

    def subscribe_queue(self, maxsize: int = 512) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=maxsize)
        with self._lock:
            for event in self._sticky.values():
                q.put_nowait(event)
            for event in self._history:
                q.put_nowait(event)
            self._queues.append(q)
        return q

    def unsubscribe_queue(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def on(self, callback: Callable[[Event], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def last(self, type_: str) -> Event | None:
        with self._lock:
            return self._sticky.get(type_)
