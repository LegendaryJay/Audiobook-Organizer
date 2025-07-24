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
    
    def __init__(self, media_root: str, check_interval: int = 30, notify_callback=None):
        self.media_root = Path(media_root) 
        self.check_interval = check_interval
        self.known_files: Dict[str, float] = {}
        self.running = False
        self.thread = None
        self.notify_callback = notify_callback
        
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
        """Trigger a library rescan with intelligent scanning and cleanup"""
        try:
            print("File changes detected - rescanning library...")
            
            # Notify frontend that scan is starting
            if self.notify_callback:
                self.notify_callback('scan_started', 'File changes detected - starting library rescan', {
                    'timestamp': time.time()
                })
            
            # Import tracker for intelligent scanning
            from audiobook_tracker import AudiobookTracker
            from pathlib import Path
            
            # Initialize tracker with proper paths
            metadata_dir = Path(__file__).parent / "metadata"
            covers_dir = Path(__file__).parent / "covers"
            tracker = AudiobookTracker(metadata_dir, covers_dir, str(self.media_root))
            
            # Use intelligent scanning - only process changed folders
            folders_to_scan, current_folders = tracker.get_folders_to_scan()
            
            if folders_to_scan:
                print(f"Scanning {len(folders_to_scan)} changed folders...")
                # Import the specialized function for processing specific folders
                from metadata_extractor import process_specific_folders
                count = process_specific_folders(str(self.media_root), folders_to_scan)
                print(f"Processed {count} new/changed audiobooks.")
            else:
                print("No folder changes detected during rescan.")
                count = 0
            
            # Update tracking summary after scan
            tracker.update_tracking_after_scan(count)
            
            # Automatic cleanup of orphaned files
            cleanup_count = {'metadata': 0, 'covers': 0}
            try:
                print("Performing automatic cleanup of orphaned data...")
                cleanup_report = tracker.cleanup_orphaned_data(dry_run=False)
                cleanup_count['metadata'] = cleanup_report['orphaned_metadata_count']
                cleanup_count['covers'] = cleanup_report['orphaned_covers_count']
                
                if cleanup_count['metadata'] > 0 or cleanup_count['covers'] > 0:
                    print(f"🧹 Cleaned up {cleanup_count['metadata']} orphaned metadata files and {cleanup_count['covers']} orphaned covers")
            except Exception as e:
                print(f"Warning: Could not perform automatic cleanup: {e}")
            
            print("Library rescan complete.")
            
            # Notify frontend that scan is complete
            if self.notify_callback:
                self.notify_callback('scan_complete', f'Library rescan completed: {count} audiobooks processed, {cleanup_count["metadata"]} orphaned metadata cleaned, {cleanup_count["covers"]} orphaned covers cleaned', {
                    'timestamp': time.time(),
                    'triggered_by': 'file_watcher',
                    'count': count,
                    'cleanup': cleanup_count
                })
                
        except Exception as e:
            print(f"Error during rescan: {e}")
            if self.notify_callback:
                self.notify_callback('scan_error', f'Library rescan failed: {str(e)}', {
                    'error': str(e),
                    'timestamp': time.time()
                })


def start_polling_watcher(media_root: str, check_interval: int = 30, notify_callback=None):
    """Start the polling file watcher"""
    watcher = PollingFileWatcher(media_root, check_interval, notify_callback)
    watcher.start()
    
    try:
        # Keep the thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()


def start_file_watcher_safe(media_root: str, notify_callback=None):
    """Start file watcher with fallback to polling if watchdog fails"""
    try:
        # Try to import and test watchdog first
        from watchdog.observers import Observer
        from file_watcher import AudioFileHandler
        
        # Test if we can create an observer (this is where the error usually occurs)
        test_observer = Observer()
        test_handler = AudioFileHandler(media_root, notify_callback)
        test_observer.schedule(test_handler, media_root, recursive=True)
        test_observer.start()
        print(f"Started watchdog file watcher for {media_root}")
        
        # If we get here, watchdog is working
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            test_observer.stop()
            print("Watchdog file watcher stopped.")
        test_observer.join()
        
    except Exception as e:
        print(f"Watchdog file watcher failed: {e}")
        print("Falling back to polling-based file watcher...")
        
        # Create and start polling watcher instead
        watcher = PollingFileWatcher(media_root, check_interval=60, notify_callback=notify_callback)
        watcher.start()
        
        # Keep the polling watcher running
        try:
            while watcher.running:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
