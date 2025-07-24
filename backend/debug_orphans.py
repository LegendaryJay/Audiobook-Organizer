#!/usr/bin/env python3

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from audiobook_tracker import AudiobookTracker
import json

# Initialize tracker
tracker = AudiobookTracker(
    metadata_dir=Path("metadata"),
    covers_dir=Path("covers"), 
    media_root="Z:/Media"
)

print("=== DEBUG: Orphan Detection ===")

# Load tracking summary
summary = tracker.load_summary()
print(f"Tracked folders: {list(summary.get('tracked_folders', {}).keys())}")

# Get current file structure
current_folders, current_files = tracker.get_current_file_structure()
print(f"Current folders: {list(current_folders.keys())}")
print(f"Current files: {list(current_files)}")

# Check each metadata file
print("\n=== Checking Metadata Files ===")
for metadata_file in tracker.metadata_dir.glob('*.json'):
    if metadata_file.name == 'tracking_summary.json':
        continue
        
    print(f"\nChecking: {metadata_file.name}")
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    paths = metadata.get('original', {}).get('paths', [])
    print(f"  Paths in metadata: {paths}")
    
    for path in paths:
        normalized_path = path.replace('/', '\\')
        folder_path = str(Path(path).parent)
        
        print(f"    Path: {path}")
        print(f"    Normalized: {normalized_path}")
        print(f"    Folder: {folder_path}")
        print(f"    File exists: {normalized_path in current_files}")
        print(f"    Folder tracked: {folder_path in summary.get('tracked_folders', {})}")

print("\n=== Orphan Detection Result ===")
orphaned_metadata, orphaned_covers = tracker.find_orphaned_metadata()
print(f"Found {len(orphaned_metadata)} orphaned metadata files")
print(f"Found {len(orphaned_covers)} orphaned covers")

for item in orphaned_metadata:
    print(f"  Orphaned: {item['title']} - {item['metadata_file'].name}")
