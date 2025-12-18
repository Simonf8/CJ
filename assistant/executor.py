"""
Action executor module.
Handles opening applications, files, URLs, and system actions.
"""

import subprocess
import os
import webbrowser
import ctypes
from typing import Optional
from urllib.parse import quote_plus


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
    """Executes desktop actions like opening apps, files, URLs, and system controls."""
    
    def __init__(self):
        self._volume_interface = None
    
    def execute(self, action: str, target: Optional[str]) -> bool:
        """
        Execute an action.
        
        Args:
            action: Action type
            target: Target path, URL, app name, or parameter
            
        Returns:
            True if action succeeded, False otherwise
        """
        action_map = {
            "open_app": self._open_app,
            "open_file": self._open_file,
            "open_url": self._open_url,
            "search_google": self._search_google,
            "search_youtube": self._search_youtube,
            "volume_up": lambda t: self._set_volume("up"),
            "volume_down": lambda t: self._set_volume("down"),
            "volume_mute": lambda t: self._set_volume("mute"),
            "volume_set": self._set_volume_level,
            "media_play_pause": lambda t: self._media_control("play_pause"),
            "media_next": lambda t: self._media_control("next"),
            "media_prev": lambda t: self._media_control("prev"),
            "lock_screen": lambda t: self._lock_screen(),
            "screenshot": lambda t: self._take_screenshot(),
            "shutdown": lambda t: self._power_control("shutdown"),
            "restart": lambda t: self._power_control("restart"),
            "sleep": lambda t: self._power_control("sleep"),
            "speak": lambda t: True,
        }
        
        handler = action_map.get(action)
        if handler:
            return handler(target)
        return False
    
    def _open_app(self, app_name: str) -> bool:
        """Open a desktop application by name."""
        if not app_name:
            return False
        app_lower = app_name.lower().strip()
        executable = APP_ALIASES.get(app_lower, app_lower)
        
        try:
            if ":" in executable:
                os.startfile(executable)
                return True
            
            result = subprocess.run(
                f'start "" "{executable}"',
                shell=True,
                capture_output=True
            )
            
            if result.returncode == 0:
                return True
            
            result = subprocess.run(
                f'where {executable}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                full_path = result.stdout.strip().split('\n')[0]
                os.startfile(full_path)
                return True
            
            return False
        except Exception:
            return False
    
    def _open_file(self, path: str) -> bool:
        """Open a file or folder."""
        if not path:
            return False
        try:
            path = os.path.expanduser(path)
            
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
        if not url:
            return False
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return True
        except Exception:
            return False
    
    def _search_google(self, query: str) -> bool:
        """Search Google for a query."""
        if not query:
            return False
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        return self._open_url(url)
    
    def _search_youtube(self, query: str) -> bool:
        """Search YouTube for a query."""
        if not query:
            return False
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        return self._open_url(url)
    
    def _get_volume_interface(self):
        """Get Windows volume interface (lazy load)."""
        if self._volume_interface is None:
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            except Exception:
                pass
        return self._volume_interface
    
    def _set_volume(self, action: str) -> bool:
        """Control system volume."""
        try:
            volume = self._get_volume_interface()
            if not volume:
                return False
            
            if action == "mute":
                current_mute = volume.GetMute()
                volume.SetMute(not current_mute, None)
            elif action == "up":
                current = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
            elif action == "down":
                current = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
            return True
        except Exception:
            return False
    
    def _set_volume_level(self, level: str) -> bool:
        """Set volume to specific level (0-100)."""
        try:
            volume = self._get_volume_interface()
            if not volume:
                return False
            level_int = int(level)
            volume.SetMasterVolumeLevelScalar(level_int / 100.0, None)
            return True
        except Exception:
            return False
    
    def _media_control(self, action: str) -> bool:
        """Control media playback using virtual key codes."""
        try:
            import pyautogui
            key_map = {
                "play_pause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
            }
            key = key_map.get(action)
            if key:
                pyautogui.press(key)
                return True
            return False
        except Exception:
            return False
    
    def _lock_screen(self) -> bool:
        """Lock the Windows screen."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception:
            return False
    
    def _take_screenshot(self) -> bool:
        """Take a screenshot and save to Downloads."""
        try:
            import pyautogui
            from datetime import datetime
            
            downloads = os.path.expanduser("~/Downloads")
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(downloads, filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            return True
        except Exception:
            return False
    
    def _power_control(self, action: str) -> bool:
        """Control power state: shutdown, restart, sleep."""
        try:
            if action == "shutdown":
                subprocess.run("shutdown /s /t 5", shell=True)
            elif action == "restart":
                subprocess.run("shutdown /r /t 5", shell=True)
            elif action == "sleep":
                # Put computer to sleep using shutdown /h for hibernate
                # or use rundll32 with different params
                os.system('rundll32.exe powrprof.dll,SetSuspendState Sleep')
            return True
        except Exception:
            return False

