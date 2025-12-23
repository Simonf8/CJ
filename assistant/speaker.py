"""
Text-to-speech module using Edge TTS.
High-quality Microsoft neural voice (Ryan - British male).
"""

import asyncio
import os
import tempfile
import threading
import time


class Speaker:
    """Text-to-speech using Edge TTS."""
    
    # British male voice
    VOICE = "en-GB-RyanNeural"
    
    def __init__(self):
        self._lock = threading.Lock()
    
    def speak(self, text: str) -> None:
        """Speak text synchronously using Edge TTS."""
        with self._lock:
            try:
                asyncio.run(self._speak_async(text))
            except Exception as e:
                print(f"[Speaker] Error: {e}")
    
    async def _speak_async(self, text: str) -> None:
        """Generate and play speech."""
        import edge_tts
        
        temp_file = os.path.join(tempfile.gettempdir(), "simon_tts.mp3")
        
        try:
            communicate = edge_tts.Communicate(text, self.VOICE)
            await communicate.save(temp_file)
            
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                self._play_audio(temp_file)
        finally:
            self._cleanup_file(temp_file)
    
    def _play_audio(self, file_path: str) -> None:
        """Play audio file using pygame."""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            pygame.mixer.quit()
        except Exception as e:
            print(f"[Speaker] Playback error: {e}")
            try:
                os.startfile(file_path)
                time.sleep(3)
            except Exception:
                pass
    
    def _cleanup_file(self, file_path: str) -> None:
        """Remove temporary file."""
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception:
                pass
    
    def speak_async(self, text: str, on_complete=None) -> None:
        """Speak text in background thread."""
        def _speak():
            self.speak(text)
            if on_complete:
                on_complete()
        
        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()
