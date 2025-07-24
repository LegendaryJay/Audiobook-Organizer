"""
Alternative file watcher using polling instead of OS events
This avoids the Python 3.13 threading issues with watchdog
"""

import time
import threading
from pathlib import Path
from typing import Dict, Set
from metadata_extractor import process_all_audiobooks, is_audio_file

class PollingFileWatcher:
    """File watcher that uses polling instead of OS events"""
    
    def __init__(self, media_root: str, check_interval: int = 30):
        self.media_root = Path(media_root)
        self.check_interval = check_interval
        self.known_files: Dict[str, float] = {}
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the polling watcher"""
        if not self.media_root.exists():
            print(f"Warning: Media root {self.media_root} does not exist. File watching disabled.")
            return
            
        self.running = True
        self._scan_initial()
        
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print(f"Started polling file watcher for {self.media_root} (checking every {self.check_interval}s)")
    
    def stop(self):
        """Stop the polling watcher"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("Polling file watcher stopped.")
    
    def _scan_initial(self):
        """Initial scan to build baseline"""
        print("Building initial file index...")
        for audio_file in self._get_audio_files():
            try:
                mtime = audio_file.stat().st_mtime
                self.known_files[str(audio_file)] = mtime
            except (OSError, PermissionError):
                continue
        print(f"Indexed {len(self.known_files)} audio files")
    
    def _get_audio_files(self):
        """Get all audio files in the media root"""
        audio_extensions = {'.mp3', '.m4a', '.m4b', '.flac', '.wav', '.ogg', '.aac', '.wma'}
        
        for file_path in self.media_root.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                yield file_path
    
    def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                time.sleep(self.check_interval)
                if not self.running:
                    break
                    
                self._check_for_changes()
                    
            except Exception as e:
                print(f"Error in file watcher: {e}")
                time.sleep(self.check_interval)
    
    def _check_for_changes(self):
        """Check for file changes"""
        current_files = {}
        changes_detected = False
        
        # Scan current files
        for audio_file in self._get_audio_files():
            try:
                file_path = str(audio_file)
                mtime = audio_file.stat().st_mtime
                current_files[file_path] = mtime
                
                # Check for new or modified files
                if file_path not in self.known_files:
                    print(f"New audio file detected: {audio_file.name}")
                    changes_detected = True
                elif self.known_files[file_path] != mtime:
                    print(f"Modified audio file detected: {audio_file.name}")
                    changes_detected = True
                    
            except (OSError, PermissionError):
                continue
        
        # Check for deleted files
        deleted_files = set(self.known_files.keys()) - set(current_files.keys())
        if deleted_files:
            for deleted in deleted_files:
                print(f"Deleted audio file detected: {Path(deleted).name}")
            changes_detected = True
        
        # Update known files
        self.known_files = current_files
        
        # Trigger rescan if changes detected
        if changes_detected:
            self._trigger_rescan()
    
    def _trigger_rescan(self):
        """Trigger a library rescan"""
        try:
            print("File changes detected - rescanning library...")
            process_all_audiobooks(str(self.media_root))
            print("Library rescan complete.")
        except Exception as e:
            print(f"Error during rescan: {e}")


def start_polling_watcher(media_root: str, check_interval: int = 30):
    """Start the polling file watcher"""
    watcher = PollingFileWatcher(media_root, check_interval)
    watcher.start()
    
    try:
        # Keep the thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()


def start_file_watcher_safe(media_root: str):
    """Start file watcher with fallback to polling if watchdog fails"""
    try:
        # Try the original watchdog approach first
        from file_watcher import start_file_watcher
        start_file_watcher(media_root)
    except Exception as e:
        print(f"Watchdog file watcher failed: {e}")
        print("Falling back to polling-based file watcher...")
        start_polling_watcher(media_root, check_interval=60)  # Check every minute
