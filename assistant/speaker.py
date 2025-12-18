"""
Text-to-speech module using pyttsx3.
Provides offline speech synthesis.
"""

import pyttsx3
import threading
from typing import Optional


class Speaker:
    """Text-to-speech using pyttsx3."""
    
    def __init__(self, rate: int = 175, voice_index: int = 0):
        """
        Initialize speaker.
        
        Args:
            rate: Speech rate (words per minute). Default 175.
            voice_index: Index of voice to use. 0 = first available.
        """
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)
        
        # Set voice if available
        voices = self._engine.getProperty("voices")
        if voices and voice_index < len(voices):
            self._engine.setProperty("voice", voices[voice_index].id)
        
        self._lock = threading.Lock()
    
    def speak(self, text: str) -> None:
        """Speak text synchronously."""
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()
    
    def speak_async(self, text: str, on_complete: Optional[callable] = None) -> None:
        """Speak text in background thread."""
        def _speak():
            self.speak(text)
            if on_complete:
                on_complete()
        
        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()
    
    def stop(self) -> None:
        """Stop current speech."""
        self._engine.stop()
    
    def set_rate(self, rate: int) -> None:
        """Set speech rate."""
        self._engine.setProperty("rate", rate)
    
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._engine.setProperty("volume", max(0.0, min(1.0, volume)))
