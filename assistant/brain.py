"""
Ollama LLM integration for command understanding.
Parses natural language commands into structured actions.
"""

import json
import ollama
from typing import TypedDict, Optional, List, Dict
from datetime import datetime

from .memory import Memory
from .commands import CustomCommands


class Action(TypedDict):
    action: str
    target: Optional[str]
    response: str


SYSTEM_PROMPT = """You are Simon, a helpful desktop voice assistant. Your job is to understand user commands and return structured JSON responses.

You MUST respond with valid JSON only, no other text. The JSON must have this structure:
{
    "action": "<action_type>",
    "target": "<target parameter>",
    "response": "<what to say back to the user>"
}

Available actions:
- "open_app": Open an application. Target = app name (chrome, notepad, vscode, spotify)
- "open_file": Open a file/folder. Target = path
- "open_url": Open a website. Target = URL
- "search_google": Search Google. Target = search query
- "search_youtube": Search YouTube. Target = search query
- "volume_up": Increase volume. Target = null
- "volume_down": Decrease volume. Target = null
- "volume_mute": Toggle mute. Target = null
- "volume_set": Set volume level. Target = 0-100
- "media_play_pause": Play/pause media. Target = null
- "media_next": Next track. Target = null
- "media_prev": Previous track. Target = null
- "lock_screen": Lock the computer. Target = null
- "screenshot": Take a screenshot. Target = null
- "shutdown": Shut down the computer. Target = null
- "restart": Restart the computer. Target = null
- "sleep": Put computer to sleep. Target = null
- "speak": Just respond verbally. Target = null

Examples:
User: "open chrome" -> {"action": "open_app", "target": "chrome", "response": "Opening Chrome"}
User: "search google for python tutorials" -> {"action": "search_google", "target": "python tutorials", "response": "Searching Google for python tutorials"}
User: "turn up the volume" -> {"action": "volume_up", "target": null, "response": "Turning up the volume"}
User: "what time is it" -> {"action": "speak", "target": null, "response": "It's 3:45 PM"}
User: "lock my computer" -> {"action": "lock_screen", "target": null, "response": "Locking your computer"}
User: "take a screenshot" -> {"action": "screenshot", "target": null, "response": "Taking a screenshot"}
User: "shut down" -> {"action": "shutdown", "target": null, "response": "Shutting down in 5 seconds"}
User: "restart computer" -> {"action": "restart", "target": null, "response": "Restarting in 5 seconds"}

Be concise and helpful. Use context from previous messages when relevant.
"""


class Brain:
    """Ollama-powered command processor with memory and custom commands."""
    
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.client = ollama.Client()
        self.memory = Memory(max_messages=10)
        self.custom_commands = CustomCommands()
    
    def process(self, command: str) -> Action:
        """Process a voice command and return structured action."""
        # Check for custom commands first
        custom_actions = self.custom_commands.get_command(command)
        if custom_actions:
            # Return the first action; main.py will handle multiple
            return {
                "action": "custom",
                "target": custom_actions,
                "response": f"Executing {command}"
            }
        
        # Add to memory
        self.memory.add_user_message(command)
        
        # Build context with time and conversation history
        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # Build messages with history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add recent conversation context
        for msg in self.memory.get_context()[:-1]:  # Exclude the current message
            messages.append(msg)
        
        # Add current command with time context
        user_msg = f"Current time: {current_time}, Date: {current_date}\n\nUser command: {command}"
        messages.append({"role": "user", "content": user_msg})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.3}
            )
            
            content = response["message"]["content"]
            action = self._parse_response(content)
            
            # Store assistant response in memory
            self.memory.add_assistant_message(action["response"])
            
            return action
            
        except ollama.ResponseError as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Sorry, Ollama error: {e}"
            }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Sorry, something went wrong: {e}"
            }
    
    def _parse_response(self, content: str) -> Action:
        """Parse LLM response into Action dict."""
        try:
            content = content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            return {
                "action": data.get("action", "speak"),
                "target": data.get("target"),
                "response": data.get("response", "Done")
            }
        except json.JSONDecodeError:
            return {
                "action": "speak",
                "target": None,
                "response": content if content else "I didn't understand that."
            }
    
    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()
    
    def get_memory_summary(self) -> str:
        """Get summary of recent conversation."""
        return self.memory.get_summary()
