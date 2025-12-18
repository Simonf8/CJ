"""
Popup UI module with transparent video hologram.
Shows only the hologram, no window frame.
"""

import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Optional
import threading
import cv2
import os


class PopupWindow:
    """Popup window with transparent video hologram."""
    
    # Transparent color key
    TRANSPARENT_COLOR = "#010101"
    
    def __init__(self):
        self._root: Optional[ctk.CTk] = None
        self._video_label: Optional[ctk.CTkLabel] = None
        self._main_label: Optional[ctk.CTkLabel] = None
        self._status_label: Optional[ctk.CTkLabel] = None
        self._visible = False
        self._setup_done = threading.Event()
        self._playing = False
        self._video_cap = None
        self._speaking = False
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def _get_video_path(self) -> str:
        """Get path to video file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "cj.mp4")
    
    def _create_window(self) -> None:
        """Create the popup window with transparency."""
        self._root = ctk.CTk()
        self._root.title("Simon")
        
        width, height = 500, 500
        
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self._root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Remove window decorations
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        
        # Make transparent color see-through
        self._root.configure(fg_color=self.TRANSPARENT_COLOR)
        self._root.attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        
        # Main frame with transparent background
        main_frame = ctk.CTkFrame(
            self._root,
            fg_color=self.TRANSPARENT_COLOR,
            corner_radius=0
        )
        main_frame.pack(fill="both", expand=True)
        
        # Video display using regular tkinter Label for transparency
        self._video_label = ctk.CTkLabel(
            main_frame,
            text="",
            fg_color=self.TRANSPARENT_COLOR
        )
        self._video_label.pack(pady=(10, 5))
        
        # Status label with transparent background
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
            wraplength=460,
            justify="center"
        )
        self._main_label.pack(pady=(5, 15), padx=15)
        
        self._root.withdraw()
        self._setup_done.set()
    
    def _play_video(self) -> None:
        """Video playback loop with black to transparent."""
        if not self._playing:
            return
        
        video_path = self._get_video_path()
        
        if self._video_cap is None or not self._video_cap.isOpened():
            if os.path.exists(video_path):
                self._video_cap = cv2.VideoCapture(video_path)
            else:
                return
        
        ret, frame = self._video_cap.read()
        
        if not ret:
            self._video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._video_cap.read()
        
        if ret:
            # Convert frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (480, 320))
            
            # Replace black pixels with transparent color
            # Black threshold (adjust if needed)
            threshold = 30
            mask = (frame[:, :, 0] < threshold) & \
                   (frame[:, :, 1] < threshold) & \
                   (frame[:, :, 2] < threshold)
            
            # Set black pixels to the transparent color (1, 1, 1)
            frame[mask] = [1, 1, 1]
            
            # Convert to PIL Image
            image = Image.fromarray(frame)
            photo = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(480, 320)
            )
            
            self._video_label.configure(image=photo)
            self._video_label.image = photo
        
        if self._playing:
            self._root.after(33, self._play_video)
    
    def run(self) -> None:
        """Run the UI."""
        self._create_window()
        self._root.mainloop()
    
    def show(self) -> None:
        """Show popup and start video."""
        if self._root and not self._visible:
            self._root.after(0, self._do_show)
    
    def _do_show(self) -> None:
        self._root.deiconify()
        self._visible = True
        self._playing = True
        self._speaking = False
        self.set_status("Listening...")
        self.set_text("")
        self._play_video()
    
    def hide(self) -> None:
        """Hide popup and stop video."""
        if self._root and self._visible:
            self._root.after(0, self._do_hide)
    
    def _do_hide(self) -> None:
        self._playing = False
        self._speaking = False
        if self._video_cap:
            self._video_cap.release()
            self._video_cap = None
        self._root.withdraw()
        self._visible = False
    
    def set_text(self, text: str) -> None:
        if self._main_label:
            self._root.after(0, lambda: self._main_label.configure(text=text))
    
    def set_status(self, status: str) -> None:
        if self._status_label:
            self._root.after(0, lambda: self._status_label.configure(text=status))
    
    def set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
    
    def hide_after(self, ms: int) -> None:
        if self._root:
            self._root.after(ms, self._do_hide)
    
    def quit(self) -> None:
        self._playing = False
        if self._video_cap:
            self._video_cap.release()
        if self._root:
            self._root.after(0, self._root.quit)
    
    def is_visible(self) -> bool:
        return self._visible
    
    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._setup_done.wait(timeout)
