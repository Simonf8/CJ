"""Test Edge TTS fallback."""
import asyncio
import os
import subprocess
import tempfile

async def test_edge_tts():
    import edge_tts
    
    text = "Hello, I am the Edge TTS fallback voice."
    voice = "en-GB-RyanNeural"
    temp_file = os.path.join(tempfile.gettempdir(), "test_edge.mp3")
    
    print(f"Generating speech to: {temp_file}")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(temp_file)
    
    if os.path.exists(temp_file):
        size = os.path.getsize(temp_file)
        print(f"File created: {size} bytes")
        
        # Play
        print("Playing audio...")
        subprocess.run(
            f'powershell -c "Add-Type -AssemblyName presentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open(\'{temp_file}\'); Start-Sleep -Milliseconds 300; $p.Play(); Start-Sleep -Seconds 3; $p.Close()"',
            shell=True
        )
        print("Done")
    else:
        print("File not created!")

asyncio.run(test_edge_tts())
