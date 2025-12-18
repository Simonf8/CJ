# Simon - Personal Voice Assistant

A Jarvis-like desktop voice assistant with push-to-talk activation, powered by local LLM.

## Features

- **Push-to-Talk**: Press `Ctrl+Space` to activate (mic not always on)
- **Natural Voice**: Microsoft Neural TTS (Ryan - British male)
- **Local AI**: Uses Ollama for command understanding (privacy-focused)
- **Hologram UI**: Animated transparent popup
- **Desktop Actions**:
  - Open apps, files, URLs
  - Control volume and media
  - Search Google/YouTube
  - Lock screen, screenshot
  - Shutdown, restart, sleep
- **Custom Commands**: Define your own shortcuts
- **System Tray**: Runs quietly in background
- **Auto-Start**: Optional startup with Windows

## Requirements

- Windows 10/11
- Python 3.10+
- [Ollama](https://ollama.com/) with a model (e.g., `llama3.2`)
- Microphone
- Internet (for Edge TTS voice)

## Installation

```bash
# Clone the repo
git clone https://github.com/Simonf8/CJ.git
cd CJ

# Install dependencies
pip install -r requirements.txt

# Install Ollama and pull a model
# Download from https://ollama.com/download
ollama pull llama3.2

# Run Simon
python main.py
```

## Usage

1. Press **Ctrl+Space** to activate Simon
2. Speak your command
3. Simon responds and takes action

### Example Commands

| Command                    | Action                |
| -------------------------- | --------------------- |
| "Open Chrome"              | Opens browser         |
| "What time is it?"         | Tells current time    |
| "Search YouTube for music" | Opens YouTube search  |
| "Turn up the volume"       | Increases volume      |
| "Lock my computer"         | Locks Windows         |
| "Take a screenshot"        | Saves to Downloads    |
| "Shut down"                | Shuts down PC in 5s   |
| "Go to sleep"              | Puts PC to sleep      |
| "Goodnight"                | Custom: locks + mutes |

### Custom Commands

Edit `config/commands.json`:

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
CJ/
├── main.py              # Entry point (push-to-talk)
├── Start Simon.bat      # Quick launcher
├── requirements.txt
├── config/commands.json # Custom commands
├── omega-aco.gif        # Hologram animation
├── assistant/
│   ├── brain.py         # Ollama LLM
│   ├── executor.py      # Action execution
│   ├── speaker.py       # Edge TTS (Ryan voice)
│   ├── memory.py        # Conversation context
│   └── commands.py      # Custom commands
├── ui/
│   ├── popup.py         # Hologram popup
│   └── tray.py          # System tray
└── utils/
    └── startup.py       # Auto-start utility
```

## Configuration

### Change LLM Model

```bash
python main.py llama3.2:70b
```

### Enable Auto-Start

```python
from utils.startup import enable_startup
enable_startup()
```

### Change Voice

Edit `assistant/speaker.py` and change `VOICE`:

```python
VOICE = "en-US-GuyNeural"  # American male
# or
VOICE = "en-GB-RyanNeural"  # British male (default)
```

## Credits

- **Ollama** - Local LLM runtime
- **Edge TTS** - Microsoft neural voices
- **CustomTkinter** - Modern UI

## License

MIT License - feel free to use and modify!

---

Made by [@Simonf8](https://github.com/Simonf8)
