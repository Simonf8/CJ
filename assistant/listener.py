"""
Speech recognition and wake word detection module.
Listens continuously for the wake word "CJ" and captures commands.
"""

import speech_recognition as sr
from typing import Callable, Optional
import threading


class Listener:
    """Continuous speech listener with wake word detection."""
    
    WAKE_WORD = "cj"
    
    def __init__(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.on_wake = on_wake
        self.on_command = on_command
        self.on_error = on_error
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Adjust for ambient noise on init
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
    
    def start(self) -> None:
        """Start listening in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
    
    def _listen_loop(self) -> None:
        """Main listening loop."""
        while self._running:
            try:
                text = self._listen_once()
                if text:
                    self._process_text(text)
            except sr.UnknownValueError:
                # Speech not understood, continue listening
                pass
            except sr.RequestError as e:
                if self.on_error:
                    self.on_error(f"Speech service error: {e}")
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Listener error: {e}")
    
    def _listen_once(self) -> Optional[str]:
        """Listen for a single phrase and return transcribed text."""
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio)
                return text.lower()
            except sr.WaitTimeoutError:
                return None
    
    def _process_text(self, text: str) -> None:
        """Process transcribed text, checking for wake word."""
        # Check if wake word is present
        if self.WAKE_WORD in text:
            if self.on_wake:
                self.on_wake()
            
            # Extract command after wake word
            parts = text.split(self.WAKE_WORD, 1)
            command = parts[1].strip() if len(parts) > 1 else ""
            
            # If no command after wake word, listen for follow-up
            if not command:
                command = self._listen_for_command()
            
            if command and self.on_command:
                self.on_command(command)
    
    def _listen_for_command(self) -> Optional[str]:
        """Listen specifically for a command after wake word detected."""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                return self.recognizer.recognize_google(audio)
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            return None
    
    def listen_for_command_sync(self) -> Optional[str]:
        """Synchronous listen for a single command. Used by UI."""
        return self._listen_for_command()
