"""
Popup UI module with animated GIF hologram.
Displays omega-aco.gif with transparent background.
"""

import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence
from typing import Optional, List
import threading
import os


class PopupWindow:
    """Popup window with animated GIF hologram."""
    
    TRANSPARENT_COLOR = "#010101"
    
    def __init__(self):
        self._root: Optional[ctk.CTk] = None
        self._gif_label = None
        self._main_label: Optional[ctk.CTkLabel] = None
        self._status_label: Optional[ctk.CTkLabel] = None
        self._visible = False
        self._setup_done = threading.Event()
        self._playing = False
        self._speaking = False
        self._frames: List = []
        self._frame_index = 0
        self._gif_delay = 50
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def _get_gif_path(self) -> str:
        """Get path to GIF file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "omega-aco.gif")
    
    def _load_gif(self) -> None:
        """Load and prepare GIF frames."""
        gif_path = self._get_gif_path()
        if not os.path.exists(gif_path):
            return
        
        gif = Image.open(gif_path)
        
        # Get original size
        orig_width, orig_height = gif.size
        
        # Calculate center crop to get middle portion
        crop_margin = 0.15  # Crop 15% from each side
        left = int(orig_width * crop_margin)
        top = int(orig_height * crop_margin)
        right = int(orig_width * (1 - crop_margin))
        bottom = int(orig_height * (1 - crop_margin))
        
        # Target display size - wider horizontally
        display_size = (500, 350)
        
        self._frames = []
        
        try:
            for frame in ImageSequence.Iterator(gif):
                # Convert to RGBA
                frame = frame.convert("RGBA")
                
                # Crop to center
                frame = frame.crop((left, top, right, bottom))
                
                # Resize
                frame = frame.resize(display_size, Image.Resampling.LANCZOS)
                
                # Make black pixels transparent
                data = frame.getdata()
                new_data = []
                threshold = 30
                for item in data:
                    if item[0] < threshold and item[1] < threshold and item[2] < threshold:
                        # Replace with transparent color (1, 1, 1, 255)
                        new_data.append((1, 1, 1, 255))
                    else:
                        new_data.append(item)
                frame.putdata(new_data)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(frame)
                self._frames.append(photo)
            
            # Get delay from GIF
            try:
                self._gif_delay = gif.info.get('duration', 50)
            except Exception:
                self._gif_delay = 50
                
        except Exception as e:
            print(f"[Popup] Error loading GIF: {e}")
    
    def _create_window(self) -> None:
        """Create the popup window."""
        self._root = ctk.CTk()
        self._root.title("Simon")
        
        width, height = 550, 480
        
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self._root.geometry(f"{width}x{height}+{x}+{y}")
        
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.configure(fg_color=self.TRANSPARENT_COLOR)
        self._root.attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        
        # Main frame
        main_frame = ctk.CTkFrame(
            self._root,
            fg_color=self.TRANSPARENT_COLOR,
            corner_radius=0
        )
        main_frame.pack(fill="both", expand=True)
        
        # Load GIF frames
        self._load_gif()
        
        # GIF display using tkinter Label for proper image handling
        import tkinter as tk
        self._gif_label = tk.Label(
            main_frame,
            bg=self.TRANSPARENT_COLOR,
            borderwidth=0,
            highlightthickness=0
        )
        self._gif_label.pack(pady=(10, 5))
        
        if self._frames:
            self._gif_label.configure(image=self._frames[0])
        
        # Status label
        self._status_label = ctk.CTkLabel(
            main_frame,
            text="Listening...",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#00d4ff",
            fg_color=self.TRANSPARENT_COLOR
        )
        self._status_label.pack(pady=(10, 5))
        
        # Text display
        self._main_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="#80d0ff",
            fg_color=self.TRANSPARENT_COLOR,
            wraplength=520,
            justify="center"
        )
        self._main_label.pack(pady=(5, 15), padx=15)
        
        self._root.withdraw()
        self._setup_done.set()
    
    def _animate_gif(self) -> None:
        """Animate the GIF frames."""
        if not self._playing or not self._frames:
            return
        
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self._gif_label.configure(image=self._frames[self._frame_index])
        
        if self._playing:
            self._root.after(self._gif_delay, self._animate_gif)
    
    def run(self) -> None:
        """Run the UI."""
        self._create_window()
        self._root.mainloop()
    
    def show(self) -> None:
        """Show popup and start animation (thread-safe)."""
        if self._root and not self._visible:
            try:
                self._root.after(0, self._do_show)
            except RuntimeError:
                # Called from wrong thread - ignore
                pass
    
    def _do_show(self) -> None:
        self._root.deiconify()
        self._visible = True
        self._playing = True
        self._speaking = False
        self._frame_index = 0
        self.set_status("Listening...")
        self.set_text("")
        self._animate_gif()
    
    def hide(self) -> None:
        """Hide popup (thread-safe)."""
        if self._root and self._visible:
            try:
                self._root.after(0, self._do_hide)
            except RuntimeError:
                pass
    
    def _do_hide(self) -> None:
        self._playing = False
        self._speaking = False
        self._root.withdraw()
        self._visible = False
    
    def set_text(self, text: str) -> None:
        if self._main_label:
            try:
                self._root.after(0, lambda: self._main_label.configure(text=text))
            except RuntimeError:
                pass
    
    def set_status(self, status: str) -> None:
        if self._status_label:
            try:
                self._root.after(0, lambda: self._status_label.configure(text=status))
            except RuntimeError:
                pass
    
    def set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
    
    def hide_after(self, ms: int) -> None:
        if self._root:
            try:
                self._root.after(ms, self._do_hide)
            except RuntimeError:
                pass
    
    def quit(self) -> None:
        self._playing = False
        if self._root:
            self._root.after(0, self._root.quit)
    
    def is_visible(self) -> bool:
        return self._visible
    
    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._setup_done.wait(timeout)
