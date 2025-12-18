# CJ - Personal Voice Assistant

A Jarvis-like personal assistant that listens to your voice, understands commands via Ollama, and executes desktop actions.

## Requirements

- Python 3.10+
- Ollama installed and running
- A model pulled (e.g., `ollama pull llama3.2`)
- Working microphone

## Installation

```powershell
cd c:\Users\kefet\Downloads\CJ
pip install -r requirements.txt
```

## Usage

```powershell
python main.py
```

Say "CJ" followed by your command:

- "CJ, open Chrome"
- "CJ, open Notepad"
- "CJ, open google.com"
- "CJ, what time is it?"

## Troubleshooting

- **PyAudio install fails**: Install from wheel: `pip install pipwin && pipwin install pyaudio`
- **No audio input**: Check microphone permissions in Windows Settings
- **Ollama errors**: Ensure Ollama is running (`ollama serve`)
