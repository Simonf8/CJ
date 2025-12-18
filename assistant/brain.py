"""
Ollama LLM integration for command understanding.
Parses natural language commands into structured actions.
"""

import json
import ollama
from typing import TypedDict, Optional
from datetime import datetime


class Action(TypedDict):
    action: str  # open_app, open_file, open_url, speak
    target: Optional[str]
    response: str


SYSTEM_PROMPT = """You are CJ, a helpful desktop voice assistant. Your job is to understand user commands and return structured JSON responses.

You MUST respond with valid JSON only, no other text. The JSON must have this structure:
{
    "action": "open_app" | "open_file" | "open_url" | "speak",
    "target": "<target path, url, or app name>",
    "response": "<what to say back to the user>"
}

Action types:
- "open_app": Open a desktop application. Target should be the app name (e.g., "chrome", "notepad", "vscode", "spotify")
- "open_file": Open a file. Target should be the file path
- "open_url": Open a website. Target should be the URL (add https:// if missing)
- "speak": Just respond verbally, no action needed. Target can be null

Examples:
User: "open chrome"
{"action": "open_app", "target": "chrome", "response": "Opening Chrome for you"}

User: "go to youtube"
{"action": "open_url", "target": "https://youtube.com", "response": "Opening YouTube"}

User: "what time is it"
{"action": "speak", "target": null, "response": "It's currently 3:45 PM"}

User: "open my documents folder"
{"action": "open_file", "target": "C:/Users/Documents", "response": "Opening your Documents folder"}

Always be concise and helpful in your responses.
"""


class Brain:
    """Ollama-powered command processor."""
    
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.client = ollama.Client()
    
    def process(self, command: str) -> Action:
        """Process a voice command and return structured action."""
        # Add current time context
        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        
        context = f"Current time: {current_time}, Date: {current_date}\n\nUser command: {command}"
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                options={"temperature": 0.3}
            )
            
            content = response["message"]["content"]
            return self._parse_response(content)
            
        except ollama.ResponseError as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Sorry, I couldn't process that. Ollama error: {e}"
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
            # Try to extract JSON from response
            content = content.strip()
            
            # Handle markdown code blocks
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
            # If JSON parsing fails, treat as speak action
            return {
                "action": "speak",
                "target": None,
                "response": content if content else "I didn't understand that."
            }
