"""
Simon - Personal Voice Assistant

Push-to-talk mode: Press Ctrl+Space to activate.
"""

import threading
import sys
import keyboard

from assistant.brain import Brain
from assistant.executor import Executor
from assistant.speaker import Speaker
from assistant.listener import Listener
from ui.popup import PopupWindow
from ui.tray import SystemTray


class Simon:
    """Main Simon assistant with push-to-talk."""
    
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
        self._recognizer = None
        self._microphone = None
    
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
        keyboard.unhook_all()
        self.popup.quit()
    
    def _on_toggle_listening(self, enabled: bool) -> None:
        """Handle toggle from tray."""
        self._enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"[Simon] Push-to-talk {status}")
    
    def _on_show_popup(self) -> None:
        """Handle show popup from tray."""
        self.popup.show()
    
    def _on_hotkey(self) -> None:
        """Called when Ctrl+Space is pressed."""
        if not self._enabled or self._processing:
            return
        
        print("[Simon] Activated! Listening...")
        self._processing = True
        
        # Run in thread to not block hotkey handler
        thread = threading.Thread(target=self._process_command, daemon=True)
        thread.start()
    
    def _process_command(self) -> None:
        """Listen for and process a command."""
        import speech_recognition as sr
        
        self.popup.show()
        self.popup.set_status("Listening...")
        self.popup.set_text("")
        
        try:
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            self.popup.set_status("Processing...")
            
            try:
                command = self._recognizer.recognize_google(audio).lower()
                print(f"[Simon] Command: {command}")
                self.popup.set_text(f'"{command}"')
            except sr.UnknownValueError:
                self.popup.set_text("Didn't catch that")
                self.popup.set_speaking(True)
                self.speaker.speak("Sorry, I didn't catch that.")
                self.popup.set_speaking(False)
                self._processing = False
                self.popup.hide_after(1500)
                return
            
            # Process with brain
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
            
        except Exception as e:
            print(f"[Simon] Error: {e}")
            self.popup.set_text("Error occurred")
            self.popup.set_speaking(True)
            self.speaker.speak("Sorry, something went wrong.")
            self.popup.set_speaking(False)
        
        finally:
            self._processing = False
            self.popup.hide_after(2000)
    
    def run(self) -> None:
        """Start the assistant."""
        print("=" * 50)
        print("  Simon - Personal Voice Assistant")
        print("=" * 50)
        print("Press Ctrl+Space to activate.")
        print("Examples:")
        print("  - 'Open Chrome'")
        print("  - 'What time is it?'")
        print("  - 'Search YouTube for music'")
        print("  - 'Turn up the volume'")
        print("  - 'Goodnight' (custom command)")
        print("=" * 50)
        print("Running in system tray...\n")
        
        # Initialize speech recognition
        self._init_speech()
        
        # Register hotkey
        keyboard.add_hotkey('ctrl+space', self._on_hotkey)
        print("[Simon] Hotkey registered: Ctrl+Space")
        
        # Start system tray
        self.tray.start()
        
        # Run UI in main thread
        try:
            self.popup.run()
        except KeyboardInterrupt:
            print("\n[Simon] Shutting down...")
        finally:
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
