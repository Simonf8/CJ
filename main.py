"""
CJ - Personal Voice Assistant

Main entry point that orchestrates all components:
- Background listener for wake word detection
- Popup UI for visual feedback
- Ollama brain for command understanding
- Executor for desktop actions
- Speaker for voice responses
- System tray for background operation
"""

import threading
import sys

from assistant.listener import Listener
from assistant.brain import Brain
from assistant.executor import Executor
from assistant.speaker import Speaker
from ui.popup import PopupWindow
from ui.tray import SystemTray


class CJ:
    """Main CJ assistant orchestrator."""
    
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
        self.listener: Listener = None
        self._processing = False
        self._listening = True
    
    def _on_quit(self) -> None:
        """Handle quit from tray."""
        print("[CJ] Quitting...")
        if self.listener:
            self.listener.stop()
        self.popup.quit()
    
    def _on_toggle_listening(self, listening: bool) -> None:
        """Handle toggle listening from tray."""
        self._listening = listening
        if listening:
            print("[CJ] Resumed listening")
        else:
            print("[CJ] Paused listening")
    
    def _on_show_popup(self) -> None:
        """Handle show popup from tray."""
        self.popup.show()
    
    def _on_wake(self) -> None:
        """Called when wake word is detected."""
        if not self._listening:
            return
        print("[CJ] Wake word detected!")
        self.popup.show()
    
    def _on_command(self, command: str) -> None:
        """Called when a command is received after wake word."""
        if not self._listening or self._processing:
            return
        
        self._processing = True
        print(f"[CJ] Command: {command}")
        
        # Update UI
        self.popup.set_status("Processing...")
        self.popup.set_text(f'"{command}"')
        
        try:
            # Process with Ollama
            action = self.brain.process(command)
            print(f"[CJ] Action: {action}")
            
            # Handle custom commands (multiple actions)
            if action["action"] == "custom":
                actions_list = action["target"]
                for sub_action in actions_list:
                    self.executor.execute(sub_action["action"], sub_action.get("target"))
                response = action["response"]
            else:
                # Execute single action
                if action["action"] != "speak":
                    success = self.executor.execute(action["action"], action["target"])
                    if not success:
                        action["response"] = f"Sorry, I couldn't do that"
                response = action["response"]
            
            # Show response and speak with mouth animation
            self.popup.set_status("Speaking...")
            self.popup.set_text(response)
            self.popup.set_speaking(True)
            
            # Speak response
            self.speaker.speak(response)
            
            # Stop mouth animation after speaking
            self.popup.set_speaking(False)
            
        except Exception as e:
            print(f"[CJ] Error: {e}")
            self.popup.set_text(f"Error: {e}")
            self.popup.set_speaking(True)
            self.speaker.speak("Sorry, something went wrong.")
            self.popup.set_speaking(False)
        
        finally:
            self._processing = False
            self.popup.hide_after(2000)
    
    def _on_error(self, error: str) -> None:
        """Called on listener errors."""
        print(f"[CJ] Error: {error}")
    
    def run(self) -> None:
        """Start the assistant."""
        print("=" * 50)
        print("  Simon - Personal Voice Assistant")
        print("=" * 50)
        print("Say 'Hey Simon' followed by your command.")
        print("Examples:")
        print("  - 'Hey Simon, open Chrome'")
        print("  - 'Hey Simon, what time is it?'")
        print("  - 'Hey Simon, search YouTube for music'")
        print("  - 'Hey Simon, turn up the volume'")
        print("  - 'Hey Simon, goodnight' (custom command)")
        print("=" * 50)
        print("Running in system tray...\n")
        
        # Start system tray
        self.tray.start()
        
        # Create listener
        self.listener = Listener(
            on_wake=self._on_wake,
            on_command=self._on_command,
            on_error=self._on_error
        )
        
        # Start listener in background
        self.listener.start()
        
        # Run UI in main thread (required by tkinter)
        try:
            self.popup.run()
        except KeyboardInterrupt:
            print("\n[CJ] Shutting down...")
        finally:
            self.listener.stop()
            self.tray.stop()


def main():
    """Entry point."""
    model = "llama3.2"
    if len(sys.argv) > 1:
        model = sys.argv[1]
        print(f"Using model: {model}")
    
    assistant = CJ(model=model)
    assistant.run()


if __name__ == "__main__":
    main()
