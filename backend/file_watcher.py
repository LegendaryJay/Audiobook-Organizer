import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from metadata_extractor import process_all_audiobooks, is_audio_file

class AudioFileHandler(FileSystemEventHandler):
    """Handler for audio file system events"""
    
    def __init__(self, media_root):
        self.media_root = media_root
        self.last_scan = 0
        self.scan_delay = 5  # Wait 5 seconds before scanning after changes
    
    def on_created(self, event):
        """Handle file creation"""
        if not event.is_directory and is_audio_file(event.src_path):
            print(f"New audio file detected: {event.src_path}")
            self._schedule_scan()
    
    def on_modified(self, event):
        """Handle file modification"""
        if not event.is_directory and is_audio_file(event.src_path):
            print(f"Audio file modified: {event.src_path}")
            self._schedule_scan()
    
    def on_moved(self, event):
        """Handle file moves"""
        if not event.is_directory and (is_audio_file(event.src_path) or is_audio_file(event.dest_path)):
            print(f"Audio file moved: {event.src_path} -> {event.dest_path}")
            self._schedule_scan()
    
    def _schedule_scan(self):
        """Schedule a scan, but avoid too frequent scans"""
        current_time = time.time()
        if current_time - self.last_scan > self.scan_delay:
            self.last_scan = current_time
            try:
                print("Rescanning library due to file changes...")
                process_all_audiobooks(self.media_root)
                print("Rescan complete.")
            except Exception as e:
                print(f"Error during rescan: {e}")

def start_file_watcher(media_root):
    """Start watching for file changes"""
    if not Path(media_root).exists():
        print(f"Warning: Media root {media_root} does not exist. File watching disabled.")
        return
    
    try:
        event_handler = AudioFileHandler(media_root)
        observer = Observer()
        observer.schedule(event_handler, media_root, recursive=True)
        
        print(f"Starting file watcher for {media_root}")
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("File watcher stopped.")
        
        observer.join()
    except Exception as e:
        print(f"File watcher failed to start: {e}")
        print("Continuing without file watching. You can manually scan for changes via the API.")
        # Just sleep to keep the thread alive but inactive
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
