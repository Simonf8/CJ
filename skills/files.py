"""
File operations skill for creating, renaming, and managing files.
"""

import os
import shutil
import re
from typing import Dict, Any, Optional
from . import Skill


class FileSkill(Skill):
    """File operations via voice commands."""
    
    name = "files"
    description = "Create, rename, move, and delete files"
    triggers = ["create file", "create folder", "new file", "new folder", 
                "rename", "delete file", "delete folder", "move file"]
    
    # Default directory for file operations
    DEFAULT_DIR = os.path.expanduser("~/Desktop")
    
    def can_handle(self, command: str) -> bool:
        return any(trigger in command for trigger in self.triggers)
    
    def execute(self, command: str) -> Dict[str, Any]:
        command_lower = command.lower()
        
        if "create file" in command_lower or "new file" in command_lower:
            return self._create_file(command)
        elif "create folder" in command_lower or "new folder" in command_lower:
            return self._create_folder(command)
        elif "delete file" in command_lower:
            return self._delete_file(command)
        elif "delete folder" in command_lower:
            return self._delete_folder(command)
        elif "rename" in command_lower:
            return self._rename(command)
        elif "move file" in command_lower:
            return self._move_file(command)
        
        return {
            "action": "speak",
            "target": None,
            "response": "I'm not sure what file operation you want."
        }
    
    def _extract_filename(self, command: str, keywords: list) -> Optional[str]:
        """Extract filename from command."""
        command_lower = command.lower()
        
        for keyword in keywords:
            if keyword in command_lower:
                # Get text after keyword
                after = command_lower.split(keyword)[1].strip()
                # Clean up common phrases
                after = after.replace("called ", "").replace("named ", "")
                # Get first word/phrase (until common stop words)
                for stop in [" on ", " in ", " at ", " to "]:
                    if stop in after:
                        after = after.split(stop)[0]
                return after.strip()
        
        return None
    
    def _create_file(self, command: str) -> Dict[str, Any]:
        """Create a new file."""
        filename = self._extract_filename(command, ["create file ", "new file "])
        
        if not filename:
            return {
                "action": "speak",
                "target": None,
                "response": "What should I name the file?"
            }
        
        # Add .txt extension if none provided
        if "." not in filename:
            filename += ".txt"
        
        filepath = os.path.join(self.DEFAULT_DIR, filename)
        
        try:
            with open(filepath, "w") as f:
                f.write("")
            return {
                "action": "speak",
                "target": None,
                "response": f"Created {filename} on your desktop."
            }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't create the file: {e}"
            }
    
    def _create_folder(self, command: str) -> Dict[str, Any]:
        """Create a new folder."""
        foldername = self._extract_filename(command, ["create folder ", "new folder "])
        
        if not foldername:
            return {
                "action": "speak",
                "target": None,
                "response": "What should I name the folder?"
            }
        
        folderpath = os.path.join(self.DEFAULT_DIR, foldername)
        
        try:
            os.makedirs(folderpath, exist_ok=True)
            return {
                "action": "speak",
                "target": None,
                "response": f"Created folder {foldername} on your desktop."
            }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't create the folder: {e}"
            }
    
    def _delete_file(self, command: str) -> Dict[str, Any]:
        """Delete a file."""
        filename = self._extract_filename(command, ["delete file ", "remove file "])
        
        if not filename:
            return {
                "action": "speak",
                "target": None,
                "response": "Which file should I delete?"
            }
        
        filepath = os.path.join(self.DEFAULT_DIR, filename)
        
        # Try with common extensions if not found
        if not os.path.exists(filepath):
            for ext in [".txt", ".doc", ".docx", ".pdf"]:
                if os.path.exists(filepath + ext):
                    filepath = filepath + ext
                    break
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Deleted {os.path.basename(filepath)}."
                }
            else:
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"I couldn't find {filename} on your desktop."
                }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't delete the file: {e}"
            }
    
    def _delete_folder(self, command: str) -> Dict[str, Any]:
        """Delete a folder."""
        foldername = self._extract_filename(command, ["delete folder ", "remove folder "])
        
        if not foldername:
            return {
                "action": "speak",
                "target": None,
                "response": "Which folder should I delete?"
            }
        
        folderpath = os.path.join(self.DEFAULT_DIR, foldername)
        
        try:
            if os.path.exists(folderpath) and os.path.isdir(folderpath):
                shutil.rmtree(folderpath)
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Deleted folder {foldername}."
                }
            else:
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"I couldn't find folder {foldername} on your desktop."
                }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't delete the folder: {e}"
            }
    
    def _rename(self, command: str) -> Dict[str, Any]:
        """Rename a file or folder."""
        # Pattern: rename X to Y
        match = re.search(r"rename\s+(.+?)\s+to\s+(.+)", command.lower())
        
        if not match:
            return {
                "action": "speak",
                "target": None,
                "response": "Try saying 'rename old name to new name'."
            }
        
        old_name = match.group(1).strip()
        new_name = match.group(2).strip()
        
        old_path = os.path.join(self.DEFAULT_DIR, old_name)
        new_path = os.path.join(self.DEFAULT_DIR, new_name)
        
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Renamed {old_name} to {new_name}."
                }
            else:
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"I couldn't find {old_name}."
                }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't rename: {e}"
            }
    
    def _move_file(self, command: str) -> Dict[str, Any]:
        """Move a file to a different location."""
        # Pattern: move file X to Y
        match = re.search(r"move\s+file\s+(.+?)\s+to\s+(.+)", command.lower())
        
        if not match:
            return {
                "action": "speak",
                "target": None,
                "response": "Try saying 'move file name to folder'."
            }
        
        filename = match.group(1).strip()
        destination = match.group(2).strip()
        
        src_path = os.path.join(self.DEFAULT_DIR, filename)
        
        # Handle common destination names
        if destination in ["documents", "my documents"]:
            dest_dir = os.path.expanduser("~/Documents")
        elif destination in ["downloads"]:
            dest_dir = os.path.expanduser("~/Downloads")
        else:
            dest_dir = os.path.join(self.DEFAULT_DIR, destination)
        
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            if os.path.exists(src_path):
                shutil.move(src_path, dest_path)
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"Moved {filename} to {destination}."
                }
            else:
                return {
                    "action": "speak",
                    "target": None,
                    "response": f"I couldn't find {filename}."
                }
        except Exception as e:
            return {
                "action": "speak",
                "target": None,
                "response": f"Couldn't move the file: {e}"
            }
