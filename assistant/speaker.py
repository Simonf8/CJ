"""
Text-to-speech module using Piper TTS.
High-quality neural text-to-speech that runs locally.
"""

import subprocess
import threading
import os
import tempfile
import wave


class Speaker:
    """Text-to-speech using Piper TTS."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize speaker.
        
        Args:
            model_path: Path to Piper ONNX model. If None, uses default voice.
        """
        # Default to the bundled voice model
        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "voices", "en_US-lessac-medium.onnx")
        
        self.model_path = model_path
        self._lock = threading.Lock()
    
    def speak(self, text: str) -> None:
        """Speak text synchronously using Piper."""
        with self._lock:
            try:
                # Create a temp file for the audio
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_file = f.name
                
                # Run piper to generate audio
                result = subprocess.run(
                    ["piper", "--model", self.model_path, "--output_file", temp_file],
                    input=text,
                    text=True,
                    capture_output=True
                )
                
                if result.returncode == 0 and os.path.exists(temp_file):
                    # Play the audio using Windows built-in player
                    self._play_audio(temp_file)
                
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
            except Exception as e:
                print(f"[Speaker] Error: {e}")
    
    def _play_audio(self, file_path: str) -> None:
        """Play audio file using Windows."""
        try:
            # Use PowerShell to play audio (works on Windows)
            subprocess.run(
                ["powershell", "-c", f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"],
                capture_output=True
            )
        except Exception:
            # Fallback: try with the start command
            try:
                subprocess.run(["cmd", "/c", f"start /wait {file_path}"], capture_output=True)
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
