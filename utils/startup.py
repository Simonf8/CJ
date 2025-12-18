"""
Startup utility module.
Handles adding/removing CJ from Windows startup.
"""

import os
import sys
import winreg


STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Simon"


def is_startup_enabled() -> bool:
    """Check if startup is enabled."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except WindowsError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def enable_startup() -> bool:
    """Add CJ to Windows startup."""
    try:
        # Get the path to main.py
        main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        python_exe = sys.executable
        
        # Create the startup command
        command = f'"{python_exe}" "{main_py}"'
        
        # Add to registry
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        
        return True
    except Exception:
        return False


def disable_startup() -> bool:
    """Remove CJ from Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def toggle_startup() -> bool:
    """Toggle startup on/off. Returns new state."""
    if is_startup_enabled():
        disable_startup()
        return False
    else:
        enable_startup()
        return True
