"""
Weather skill using wttr.in free API.
"""

import urllib.request
import json
from typing import Dict, Any
from . import Skill


class WeatherSkill(Skill):
    """Get weather information."""
    
    name = "weather"
    description = "Get current weather for any location"
    triggers = ["weather", "temperature outside", "forecast"]
    
    def can_handle(self, command: str) -> bool:
        # Must explicitly mention weather-related terms
        weather_terms = ["weather", "forecast", "temperature outside", "how hot", "how cold"]
        return any(term in command for term in weather_terms)
    
    def execute(self, command: str) -> Dict[str, Any]:
        # Extract location from command
        location = self._extract_location(command)
        
        try:
            weather = self._get_weather(location)
            return {
                "action": "speak",
                "target": None,
                "response": weather
            }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Sorry, I couldn't get the weather: {e}"
            }
    
    def _extract_location(self, command: str) -> str:
        """Extract location from command."""
        # Common patterns
        patterns = ["weather in ", "weather for ", "weather at "]
        command_lower = command.lower()
        
        for pattern in patterns:
            if pattern in command_lower:
                return command_lower.split(pattern)[1].strip()
        
        # Default location
        return "London"
    
    def _get_weather(self, location: str) -> str:
        """Fetch weather from wttr.in."""
        url = f"https://wttr.in/{location}?format=j1"
        
        req = urllib.request.Request(url, headers={"User-Agent": "Simon-Assistant"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        city = area["areaName"][0]["value"]
        
        return f"In {city}, it's currently {temp_c}°C ({temp_f}°F), {desc.lower()}, with {humidity}% humidity."
