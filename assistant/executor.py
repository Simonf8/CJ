"""
Action executor module.
Handles opening applications, files, and URLs.
"""

import subprocess
import os
import webbrowser
from typing import Optional


# Common application aliases mapped to Windows executables/commands
APP_ALIASES = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    
    # Microsoft Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    
    # Development
    "vscode": "code",
    "visual studio code": "code",
    "vs code": "code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    
    # Media
    "spotify": "spotify",
    "vlc": "vlc",
    
    # System
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "calculator": "calc",
    "calc": "calc",
    "settings": "ms-settings:",
    "control panel": "control",
    
    # Communication
    "discord": "discord",
    "slack": "slack",
    "teams": "teams",
    "microsoft teams": "teams",
    "zoom": "zoom",
}


class Executor:
    """Executes desktop actions like opening apps, files, and URLs."""
    
    def execute(self, action: str, target: Optional[str]) -> bool:
        """
        Execute an action.
        
        Args:
            action: Action type (open_app, open_file, open_url, speak)
            target: Target path, URL, or app name
            
        Returns:
            True if action succeeded, False otherwise
        """
        if not target and action != "speak":
            return False
        
        if action == "open_app":
            return self._open_app(target)
        elif action == "open_file":
            return self._open_file(target)
        elif action == "open_url":
            return self._open_url(target)
        elif action == "speak":
            return True  # No action needed, just speaking
        
        return False
    
    def _open_app(self, app_name: str) -> bool:
        """Open a desktop application by name."""
        # Normalize app name
        app_lower = app_name.lower().strip()
        
        # Check for alias
        executable = APP_ALIASES.get(app_lower, app_lower)
        
        try:
            # Handle special URI schemes (like ms-settings:)
            if ":" in executable:
                os.startfile(executable)
                return True
            
            # Try to start the application
            subprocess.Popen(
                executable,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            # Try with .exe extension
            try:
                subprocess.Popen(
                    f"{executable}.exe",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except Exception:
                return False
    
    def _open_file(self, path: str) -> bool:
        """Open a file or folder."""
        try:
            # Expand user path
            path = os.path.expanduser(path)
            
            # Handle common folder shortcuts
            path_lower = path.lower()
            if "documents" in path_lower and not os.path.exists(path):
                path = os.path.expanduser("~/Documents")
            elif "downloads" in path_lower and not os.path.exists(path):
                path = os.path.expanduser("~/Downloads")
            elif "desktop" in path_lower and not os.path.exists(path):
                path = os.path.expanduser("~/Desktop")
            
            os.startfile(path)
            return True
        except Exception:
            return False
    
    def _open_url(self, url: str) -> bool:
        """Open a URL in the default browser."""
        try:
            # Ensure URL has protocol
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            webbrowser.open(url)
            return True
        except Exception:
            return False
