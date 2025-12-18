"""
Text-to-speech module using Edge TTS.
High-quality Microsoft neural voice (Ryan - British male).
"""

import asyncio
import subprocess
import threading
import os
import tempfile
import time


class Speaker:
    """Text-to-speech using Edge TTS."""
    
    # Ryan - British male voice
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
        
        # Create temp file
        temp_file = os.path.join(tempfile.gettempdir(), "simon_tts.mp3")
        
        try:
            # Generate speech
            communicate = edge_tts.Communicate(text, self.VOICE)
            await communicate.save(temp_file)
            
            # Play audio
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                self._play_audio(temp_file)
        finally:
            # Clean up
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
    
    def _play_audio(self, file_path: str) -> None:
        """Play audio file on Windows using ffplay or fallback."""
        try:
            # Try using start command which opens default player and waits
            result = subprocess.run(
                f'powershell -c "Add-Type -AssemblyName presentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open(\'{file_path}\'); Start-Sleep -Milliseconds 300; $p.Play(); while($p.Position.TotalSeconds -lt $p.NaturalDuration.TimeSpan.TotalSeconds -and $p.NaturalDuration.HasTimeSpan){{Start-Sleep -Milliseconds 100}}; $p.Close()"',
                shell=True,
                capture_output=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"[Speaker] Playback error: {e}")
            # Fallback: just open the file
            try:
                os.startfile(file_path)
                time.sleep(3)
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
