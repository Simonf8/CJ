from __future__ import annotations

import os
import re
import shutil
from typing import Optional

from ..plan import Plan
from . import Skill

KNOWN_DIRS = {
    "desktop": "~/Desktop",
    "documents": "~/Documents",
    "my documents": "~/Documents",
    "downloads": "~/Downloads",
    "pictures": "~/Pictures",
    "music": "~/Music",
    "videos": "~/Videos",
}

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(raw: str) -> Optional[str]:
    name = raw.strip().strip("'\" .")
    name = re.sub(r"\s+dot\s+", ".", name)
    if not name or name in {".", ".."} or ".." in name or _INVALID.search(name):
        return None
    return name


class FileSkill(Skill):
    name = "files"
    description = "Create, rename, move and delete files and folders on the desktop"

    _CREATE = re.compile(r"^(?:create|make|new)(?: a)?(?: new)? (file|folder|directory) (?:called |named )?(.+?)(?: on (?:the|my) desktop)?[.!]*$")
    _DELETE = re.compile(r"^(?:delete|remove|trash|bin)(?: the)? (file|folder|directory) (?:called |named )?(.+?)(?: from (?:the|my) desktop)?[.!]*$")
    _RENAME = re.compile(r"^rename(?: the)?(?: file| folder)? (.+?) to (.+?)[.!]*$")
    _MOVE = re.compile(r"^move(?: the)?(?: file| folder)? (.+?) (?:in)?to(?: my| the)? (.+?)(?: folder)?[.!]*$")

    def __init__(self, ctx, base_dir: Optional[str] = None):
        super().__init__(ctx)
        self.base_dir = base_dir or os.path.expanduser("~/Desktop")

    def can_handle(self, text: str) -> bool:
        return any(p.match(text) for p in (self._CREATE, self._DELETE, self._RENAME, self._MOVE))

    def handle(self, text: str) -> Optional[Plan]:
        if not os.path.isdir(self.base_dir):
            return Plan.say("I can't find your desktop folder.")
        if m := self._CREATE.match(text):
            return self._create(m.group(1), m.group(2))
        if m := self._DELETE.match(text):
            return self._delete(m.group(2))
        if m := self._RENAME.match(text):
            return self._rename(m.group(1), m.group(2))
        if m := self._MOVE.match(text):
            return self._move(m.group(1), m.group(2))
        return None

    def _path(self, name: str) -> Optional[str]:
        clean = safe_name(name)
        return os.path.join(self.base_dir, clean) if clean else None

    def _resolve(self, name: str) -> Optional[str]:
        path = self._path(name)
        if not path:
            return None
        if os.path.exists(path):
            return path
        stem = os.path.basename(path).lower()
        try:
            for entry in os.listdir(self.base_dir):
                if os.path.splitext(entry)[0].lower() == stem:
                    return os.path.join(self.base_dir, entry)
        except OSError:
            pass
        return None

    def _create(self, kind: str, name: str) -> Plan:
        path = self._path(name)
        if not path:
            return Plan.say("That isn't a valid name. Try something simpler.")
        if os.path.exists(path):
            return Plan.say(f"{os.path.basename(path)} already exists on your desktop.")
        if kind == "file":
            if not os.path.splitext(path)[1]:
                path += ".txt"
            open(path, "x", encoding="utf-8").close()
        else:
            os.makedirs(path)
        return Plan.say(f"Created {os.path.basename(path)} on your desktop.")

    def _delete(self, name: str) -> Plan:
        path = self._resolve(name)
        if not path:
            return Plan.say(f"I can't find {name} on your desktop.")
        try:
            from send2trash import send2trash
        except ImportError:
            return Plan.say("For safety I only delete to the Recycle Bin. Please install send2trash.")
        send2trash(path)
        return Plan.say(f"{os.path.basename(path)} moved to the Recycle Bin.")

    def _rename(self, old: str, new: str) -> Plan:
        src = self._resolve(old)
        if not src:
            return Plan.say(f"I can't find {old} on your desktop.")
        clean = safe_name(new)
        if not clean:
            return Plan.say("That new name isn't valid.")
        if not os.path.splitext(clean)[1] and os.path.isfile(src):
            clean += os.path.splitext(src)[1]
        dst = os.path.join(self.base_dir, clean)
        if os.path.exists(dst):
            return Plan.say(f"{clean} already exists.")
        os.rename(src, dst)
        return Plan.say(f"Renamed to {clean}.")

    def _move(self, name: str, destination: str) -> Plan:
        src = self._resolve(name)
        if not src:
            return Plan.say(f"I can't find {name} on your desktop.")
        dest = destination.strip().lower()
        if dest in KNOWN_DIRS:
            dest_dir = os.path.expanduser(KNOWN_DIRS[dest])
        else:
            dest_dir = self._path(destination)
            if not dest_dir or not os.path.isdir(dest_dir):
                return Plan.say(f"I can't find a folder called {destination}.")
        target = os.path.join(dest_dir, os.path.basename(src))
        if os.path.exists(target):
            return Plan.say(f"There's already a {os.path.basename(src)} there.")
        shutil.move(src, target)
        return Plan.say(f"Moved {os.path.basename(src)} to {destination}.")
