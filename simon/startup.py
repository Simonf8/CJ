from __future__ import annotations

import os
import sys

from .config import ROOT_DIR

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "Simon"


def _command() -> str:
    python = sys.executable
    pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
    if os.path.exists(pythonw):
        python = pythonw
    return f'"{python}" "{os.path.join(ROOT_DIR, "main.py")}"'


def is_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
            winreg.QueryValueEx(key, _NAME)
        return True
    except (ImportError, OSError):
        return False


def enable() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, _command())
        return True
    except (ImportError, OSError):
        return False


def disable() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _NAME)
        return True
    except (ImportError, OSError):
        return False


def toggle() -> bool:
    if is_enabled():
        disable()
        return False
    return enable()
