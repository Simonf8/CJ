from __future__ import annotations

import logging
import os
import platform
import threading
import time
from typing import Any, Dict, Optional

from .events import EventBus

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

_GB = 1024 ** 3
_net_lock = threading.Lock()
_last_net: Optional[tuple] = None


def _system_drive() -> str:
    return os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"


def snapshot() -> Optional[Dict[str, Any]]:
    global _last_net
    if psutil is None:
        return None

    vm = psutil.virtual_memory()
    try:
        du = psutil.disk_usage(_system_drive())
        disk, disk_free = du.percent, du.free / _GB
    except OSError:
        disk, disk_free = 0.0, 0.0

    up = down = 0.0
    try:
        io = psutil.net_io_counters()
        now = time.time()
        with _net_lock:
            if _last_net:
                dt = max(now - _last_net[0], 1e-3)
                up = max(0.0, (io.bytes_sent - _last_net[1]) / dt)
                down = max(0.0, (io.bytes_recv - _last_net[2]) / dt)
            _last_net = (now, io.bytes_sent, io.bytes_recv)
    except (OSError, AttributeError):
        pass

    battery = None
    try:
        b = psutil.sensors_battery()
        if b is not None:
            battery = {"percent": int(b.percent), "plugged": bool(b.power_plugged)}
    except (AttributeError, OSError, NotImplementedError):
        pass

    per_core = psutil.cpu_percent(percpu=True) or [0.0]
    return {
        "cpu": sum(per_core) / len(per_core),
        "per_core": per_core[:16],
        "cores": psutil.cpu_count(logical=True) or len(per_core),
        "ram": vm.percent,
        "ram_used_gb": (vm.total - vm.available) / _GB,
        "ram_total_gb": vm.total / _GB,
        "disk": disk,
        "disk_free_gb": disk_free,
        "net_up": up,
        "net_down": down,
        "battery": battery,
        "uptime": time.time() - psutil.boot_time(),
        "processes": len(psutil.pids()),
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
    }


def human_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


class TelemetryFeed:
    def __init__(self, bus: EventBus, interval: float = 1.0):
        self.bus = bus
        self.interval = interval
        self._stop = threading.Event()

    def start(self) -> None:
        if psutil is None:
            log.info("psutil not installed — HUD telemetry disabled")
            return
        psutil.cpu_percent(percpu=True)
        threading.Thread(target=self._loop, name="telemetry", daemon=True).start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                snap = snapshot()
                if snap:
                    self.bus.publish("telemetry", **snap)
            except Exception:
                log.debug("Telemetry sample failed", exc_info=True)

    def stop(self) -> None:
        self._stop.set()
