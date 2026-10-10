from __future__ import annotations

import re
from typing import Optional

from .. import telemetry
from ..plan import Plan
from . import Skill


class SystemSkill(Skill):
    name = "system"
    description = "System diagnostics: CPU, memory, disk, battery, network"

    _TRIGGER = re.compile(
        r"\b(system (?:status|report|check|diagnostics?)|diagnostics?|status report|run (?:a )?(?:scan|diagnostic)|"
        r"how(?:'s| is) (?:the|my) (?:system|computer|pc|machine)|battery|cpu|processor|"
        r"(?:memory|ram) usage|how much (?:memory|ram|storage|disk|space)|disk space|uptime)\b"
    )

    def can_handle(self, text: str) -> bool:
        return bool(self._TRIGGER.search(text))

    def handle(self, text: str) -> Optional[Plan]:
        snap = telemetry.snapshot()
        if snap is None:
            return Plan.say("Telemetry is unavailable. Install psutil to enable diagnostics.")

        if "battery" in text:
            b = snap.get("battery")
            if not b:
                return Plan.say("No battery detected. We're running on mains power.")
            state = "charging" if b["plugged"] else "discharging"
            return Plan.say(f"Battery at {b['percent']} percent and {state}.")
        if re.search(r"\b(cpu|processor)\b", text):
            return Plan.say(f"Processor load is {snap['cpu']:.0f} percent across {snap['cores']} cores.")
        if re.search(r"\b(memory|ram)\b", text):
            return Plan.say(f"Memory is at {snap['ram']:.0f} percent: {snap['ram_used_gb']:.1f} of "
                            f"{snap['ram_total_gb']:.0f} gigabytes in use.")
        if re.search(r"\b(disk|storage|space)\b", text):
            return Plan.say(f"Primary drive is {snap['disk']:.0f} percent full, with "
                            f"{snap['disk_free_gb']:.0f} gigabytes free.")
        if "uptime" in text:
            return Plan.say(f"System uptime is {telemetry.human_uptime(snap['uptime'])}.")

        self.ctx.bus.publish("diagnostics", snapshot=snap)
        return Plan.say(self._report(snap))

    @staticmethod
    def _report(s) -> str:
        issues = []
        if s["cpu"] > 85:
            issues.append("the processor is running hot")
        if s["ram"] > 85:
            issues.append("memory is nearly exhausted")
        if s["disk"] > 90:
            issues.append("the primary drive is almost full")
        b = s.get("battery")
        if b and b["percent"] < 20 and not b["plugged"]:
            issues.append("battery is critically low")

        parts = [
            "Diagnostics complete.",
            f"CPU at {s['cpu']:.0f} percent, memory {s['ram']:.0f} percent, "
            f"disk {s['disk']:.0f} percent.",
        ]
        if b:
            parts.append(f"Battery {b['percent']} percent.")
        parts.append(f"Uptime {telemetry.human_uptime(s['uptime'])}.")
        if issues:
            parts.append("Attention: " + ", and ".join(issues) + ".")
        else:
            parts.append("All systems nominal.")
        return " ".join(parts)
