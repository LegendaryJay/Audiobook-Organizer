#!/usr/bin/env python3
"""Debug script to understand orphan detection issues"""

from audiobook_tracker import AudiobookTracker
from pathlib import Path
import json

# Initialize tracker
metadata_dir = Path("metadata")
covers_dir = Path("covers")
media_root = "Z:/Media"

tracker = AudiobookTracker(metadata_dir, covers_dir, media_root)

print("=== DEBUGGING ORPHAN DETECTION ===")

# Load tracking summary
summary = tracker.load_summary()
print(f"\nTracking Summary:")
print(f"  tracked_folders: {list(summary.get('tracked_folders', {}).keys())}")
print(f"  audiobook_count: {summary.get('audiobook_count', 0)}")

# Get current file structure
current_folders, current_files = tracker.get_current_file_structure()
print(f"\nCurrent File Structure:")
print(f"  current_folders: {list(current_folders.keys())}")
print(f"  current_files: {list(current_files)[:3]}...")

# Check each metadata file
print(f"\n=== CHECKING METADATA FILES ===")
for metadata_file in metadata_dir.glob('*.json'):
    if metadata_file.name == 'tracking_summary.json':
        continue
        
    print(f"\nChecking: {metadata_file.name}")
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        paths = metadata.get('original', {}).get('paths', [])
        print(f"  paths: {paths}")
        
        paths_exist = False
        folder_is_tracked = False
        
        for path in paths:
            normalized_path = path.replace('/', '\\')
            if normalized_path in current_files:
                paths_exist = True
                print(f"    ✓ Path exists: {normalized_path}")
            else:
                print(f"    ✗ Path missing: {normalized_path}")
            
            folder_path = str(Path(path).parent)
            if folder_path in summary.get('tracked_folders', {}):
                folder_is_tracked = True
                print(f"    ✓ Folder tracked: {folder_path}")
            else:
                print(f"    ✗ Folder not tracked: {folder_path}")
        
        is_orphaned = not paths_exist or not folder_is_tracked
        print(f"  RESULT: {'ORPHANED' if is_orphaned else 'VALID'}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
