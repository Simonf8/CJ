# Simon - Personal Voice Assistant

A Jarvis-like desktop voice assistant with push-to-talk activation.

![Simon Demo](assets/demo.gif)

## Features

- **Push-to-Talk**: Press `Ctrl+Space` to activate
- **Jarvis Voice**: ONNX-based TTS with Marvel Jarvis voice
- **Local LLM**: Uses Ollama for command understanding (no cloud AI)
- **Desktop Actions**: Open apps, files, URLs, control volume, media
- **Custom Commands**: Define shortcuts in `config/commands.json`
- **Transparent Hologram UI**: Floating animated hologram display
- **System Tray**: Runs in background with tray menu

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) with a model installed
- Windows 10/11
- Microphone

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/simon-assistant.git
   cd simon-assistant
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install Ollama and a model**

   ```bash
   # Download from https://ollama.com/download
   ollama pull llama3.2
   ```

4. **Run Simon**
   ```bash
   python main.py
   ```

## Usage

1. Press `Ctrl+Space` to activate Simon
2. Speak your command
3. Simon will respond and take action

### Example Commands

| Command                    | Action                        |
| -------------------------- | ----------------------------- |
| "Open Chrome"              | Opens Google Chrome           |
| "What time is it?"         | Tells current time            |
| "Search YouTube for music" | Opens YouTube search          |
| "Turn up the volume"       | Increases system volume       |
| "Lock my computer"         | Locks Windows                 |
| "Take a screenshot"        | Saves screenshot to Downloads |
| "Goodnight"                | Custom: locks + mutes         |

### Custom Commands

Edit `config/commands.json` to add your own shortcuts:

```json
{
  "goodnight": [
    { "action": "lock_screen", "target": null },
    { "action": "volume_mute", "target": null }
  ],
  "morning": [
    { "action": "open_url", "target": "https://weather.com" },
    { "action": "open_app", "target": "chrome" }
  ]
}
```

## Project Structure

```
simon-assistant/
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
├── config/
│   └── commands.json    # Custom commands
├── voices/
│   └── jarvis.onnx      # Jarvis voice model
├── assistant/
│   ├── brain.py         # Ollama LLM integration
│   ├── executor.py      # Action execution
│   ├── speaker.py       # Piper TTS
│   ├── memory.py        # Conversation context
│   └── commands.py      # Custom commands
├── ui/
│   ├── popup.py         # Hologram UI
│   └── tray.py          # System tray
└── utils/
    └── startup.py       # Auto-start utility
```

## Configuration

### Change Ollama Model

```bash
python main.py llama3.2:70b
```

### Enable Auto-Start

```python
from utils.startup import enable_startup
enable_startup()
```

## License

MIT License
