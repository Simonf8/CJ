"""
Simon - Personal Voice Assistant

Activation modes:
- Say "Hey Simon" or "Simon" to activate
- Press Ctrl+Space as backup
"""

import threading
import sys
import time
import keyboard

from assistant.brain import Brain
from assistant.executor import Executor
from assistant.speaker import Speaker
from ui.popup import PopupWindow
from ui.tray import SystemTray


class Simon:
    """Main Simon assistant with wake word and hotkey activation."""
    
    WAKE_WORDS = ["hey simon", "simon", "hey saimon", "saimon"]
    CONVERSATION_TIMEOUT = 5.0  # Seconds to stay active after response
    
    def __init__(self, model: str = "llama3.2"):
        self.brain = Brain(model=model)
        self.executor = Executor()
        self.speaker = Speaker()
        self.popup = PopupWindow()
        self.tray = SystemTray(
            on_quit=self._on_quit,
            on_toggle_listening=self._on_toggle_listening,
            on_show_popup=self._on_show_popup
        )
        self._processing = False
        self._enabled = True
        self._listening = False
        self._in_conversation = False
        self._last_response_time = 0
        self._recognizer = None
        self._microphone = None
        self._stop_wake_listener = threading.Event()
        self._mic_lock = threading.Lock()  # Prevent microphone conflicts
    
    def _init_speech(self):
        """Initialize speech recognition."""
        import speech_recognition as sr
        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
    
    def _on_quit(self) -> None:
        """Handle quit."""
        print("[Simon] Quitting...")
        self._stop_wake_listener.set()
        keyboard.unhook_all()
        self.popup.quit()
    
    def _on_toggle_listening(self, enabled: bool) -> None:
        """Handle toggle from tray."""
        self._enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"[Simon] Voice activation {status}")
    
    def _on_show_popup(self) -> None:
        """Handle show popup from tray."""
        self.popup.show()
    
    def _on_hotkey(self) -> None:
        """Called when Ctrl+Space is pressed."""
        if not self._enabled or self._processing:
            return
        self._activate()
    
    def _activate(self) -> None:
        """Activate listening mode."""
        if self._processing:
            return
        
        print("[Simon] Activated! Listening...")
        self._processing = True
        self._in_conversation = True
        
        thread = threading.Thread(target=self._process_command, daemon=True)
        thread.start()
    
    def _check_wake_word(self, text: str) -> tuple:
        """Check if text contains wake word and extract command."""
        text_lower = text.lower()
        
        for wake_word in self.WAKE_WORDS:
            if wake_word in text_lower:
                # Extract command after wake word
                parts = text_lower.split(wake_word, 1)
                if len(parts) > 1:
                    command = parts[1].strip()
                    if command:
                        return True, command
                return True, None
        
        return False, None
    
    def _wake_word_listener(self) -> None:
        """Background thread that listens for wake word."""
        import speech_recognition as sr
        
        print("[Simon] Wake word listener started - say 'Hey Simon' to activate")
        
        while not self._stop_wake_listener.is_set():
            if not self._enabled or self._processing:
                time.sleep(0.1)
                continue
            
            # Check if in conversation mode (recently responded)
            if self._in_conversation:
                elapsed = time.time() - self._last_response_time
                if elapsed < self.CONVERSATION_TIMEOUT:
                    # Still in conversation, skip wake word detection
                    time.sleep(0.1)
                    continue
                else:
                    self._in_conversation = False
            
            try:
                # Skip if microphone is in use
                if not self._mic_lock.acquire(blocking=False):
                    time.sleep(0.2)
                    continue
                
                try:
                    with self._microphone as source:
                        # Short timeout for ambient listening
                        audio = self._recognizer.listen(
                            source, 
                            timeout=2, 
                            phrase_time_limit=3
                        )
                finally:
                    self._mic_lock.release()
                
                try:
                    heard = self._recognizer.recognize_google(audio).lower()
                    
                    # Check for wake word
                    has_wake_word, command = self._check_wake_word(heard)
                    
                    if has_wake_word:
                        print(f"[Simon] Wake word detected!")
                        if command:
                            # Process command immediately
                            self._processing = True
                            self._in_conversation = True
                            thread = threading.Thread(
                                target=self._process_with_command, 
                                args=(command,),
                                daemon=True
                            )
                            thread.start()
                        else:
                            # Just wake word, wait for command
                            self._activate()
                            
                except sr.UnknownValueError:
                    pass  # Nothing recognized
                except sr.RequestError:
                    time.sleep(1)
                    
            except Exception:
                time.sleep(0.5)
    
    def _process_with_command(self, command: str) -> None:
        """Process a pre-captured command."""
        self.popup.show()
        self.popup.set_status("Processing...")
        self.popup.set_text(f'"{command}"')
        print(f"[Simon] Command: {command}")
        
        try:
            self._execute_command(command)
        finally:
            self._processing = False
            self._last_response_time = time.time()
            self.popup.hide_after(2000)
    
    def _process_command(self) -> None:
        """Listen for and process a command."""
        import speech_recognition as sr
        
        self.popup.show()
        self.popup.set_status("Listening...")
        self.popup.set_text("")
        
        try:
            with self._mic_lock:
                with self._microphone as source:
                    audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            self.popup.set_status("Processing...")
            
            try:
                command = self._recognizer.recognize_google(audio).lower()
                
                # Remove wake word if present
                for ww in self.WAKE_WORDS:
                    if command.startswith(ww):
                        command = command[len(ww):].strip()
                        break
                
                print(f"[Simon] Command: {command}")
                self.popup.set_text(f'"{command}"')
                
                if command:
                    self._execute_command(command)
                else:
                    self.popup.set_text("What can I help with?")
                    self.speaker.speak("Yes? What can I help with?")
                    
            except sr.UnknownValueError:
                self.popup.set_text("Didn't catch that")
                self.speaker.speak("Sorry, I didn't catch that.")
                
        except Exception as e:
            print(f"[Simon] Error: {e}")
            self.popup.set_text("Error occurred")
            self.speaker.speak("Sorry, something went wrong.")
        
        finally:
            self._processing = False
            self._last_response_time = time.time()
            self.popup.hide_after(2000)
    
    def _execute_command(self, command: str) -> None:
        """Execute a command through the brain."""
        action = self.brain.process(command)
        print(f"[Simon] Action: {action}")
        
        # Handle custom commands
        if action["action"] == "custom":
            for sub_action in action["target"]:
                self.executor.execute(sub_action["action"], sub_action.get("target"))
            response = action["response"]
        else:
            if action["action"] != "speak":
                success = self.executor.execute(action["action"], action["target"])
                if not success:
                    action["response"] = "Sorry, I couldn't do that"
            response = action["response"]
        
        # Speak response
        self.popup.set_status("Speaking...")
        self.popup.set_text(response)
        self.popup.set_speaking(True)
        self.speaker.speak(response)
        self.popup.set_speaking(False)
    
    def run(self) -> None:
        """Start the assistant."""
        print("=" * 50)
        print("  Simon - Personal Voice Assistant")
        print("=" * 50)
        print("Say 'Hey Simon' or 'Simon' to activate")
        print("Or press Ctrl+Space")
        print("=" * 50)
        print("Examples:")
        print("  - 'Hey Simon, what time is it?'")
        print("  - 'Simon, open Chrome'")
        print("  - 'What's the weather in London?'")
        print("  - 'Remember my name is John'")
        print("=" * 50)
        print("Running in system tray...\n")
        
        # Initialize speech recognition
        self._init_speech()
        
        # Register hotkey
        keyboard.add_hotkey('ctrl+space', self._on_hotkey)
        print("[Simon] Hotkey registered: Ctrl+Space")
        
        # Start wake word listener
        wake_thread = threading.Thread(target=self._wake_word_listener, daemon=True)
        wake_thread.start()
        
        # Start system tray
        self.tray.start()
        
        # Run UI in main thread
        try:
            self.popup.run()
        except KeyboardInterrupt:
            print("\n[Simon] Shutting down...")
        finally:
            self._stop_wake_listener.set()
            keyboard.unhook_all()
            self.tray.stop()


def main():
    """Entry point."""
    model = "llama3.2"
    if len(sys.argv) > 1:
        model = sys.argv[1]
        print(f"Using model: {model}")
    
    assistant = Simon(model=model)
    assistant.run()


if __name__ == "__main__":
    main()
