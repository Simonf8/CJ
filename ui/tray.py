"""
System tray icon module.
Provides system tray presence with menu for CJ.
"""

import pystray
from PIL import Image, ImageDraw
import threading
from typing import Callable, Optional


def create_icon_image(size: int = 64, color: str = "#58a6ff") -> Image.Image:
    """Create a simple circular icon."""
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a filled circle
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color
    )
    
    # Draw "S" in the center (for Simon)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    
    # Center the text
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - margin // 2
    draw.text((x, y), text, fill="white", font=font)
    
    return image


class SystemTray:
    """System tray icon and menu."""
    
    def __init__(
        self,
        on_quit: Optional[Callable] = None,
        on_toggle_listening: Optional[Callable] = None,
        on_show_popup: Optional[Callable] = None
    ):
        self.on_quit = on_quit
        self.on_toggle_listening = on_toggle_listening
        self.on_show_popup = on_show_popup
        
        self._icon: Optional[pystray.Icon] = None
        self._listening = True
        self._thread: Optional[threading.Thread] = None
    
    def _create_menu(self) -> pystray.Menu:
        """Create the tray menu."""
        return pystray.Menu(
            pystray.MenuItem(
                "Simon - Voice Assistant",
                None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Show",
                self._on_show
            ),
            pystray.MenuItem(
                lambda item: "Pause Listening" if self._listening else "Resume Listening",
                self._on_toggle_listening
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Quit",
                self._on_quit
            )
        )
    
    def _on_show(self, icon, item) -> None:
        """Handle show menu item."""
        if self.on_show_popup:
            self.on_show_popup()
    
    def _on_toggle_listening(self, icon, item) -> None:
        """Handle toggle listening menu item."""
        self._listening = not self._listening
        if self.on_toggle_listening:
            self.on_toggle_listening(self._listening)
        # Update menu
        self._icon.update_menu()
    
    def _on_quit(self, icon, item) -> None:
        """Handle quit menu item."""
        icon.stop()
        if self.on_quit:
            self.on_quit()
    
    def _on_click(self, icon, item) -> None:
        """Handle left click on tray icon."""
        if self.on_show_popup:
            self.on_show_popup()
    
    def start(self) -> None:
        """Start the system tray icon in a background thread."""
        def run_tray():
            image = create_icon_image()
            self._icon = pystray.Icon(
                "simon",
                image,
                "Simon - Voice Assistant",
                menu=self._create_menu()
            )
            self._icon.run()
        
        self._thread = threading.Thread(target=run_tray, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the system tray icon."""
        if self._icon:
            self._icon.stop()
    
    def set_listening(self, listening: bool) -> None:
        """Update listening state."""
        self._listening = listening
        if self._icon:
            self._icon.update_menu()
