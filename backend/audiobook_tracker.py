import json
import os
from pathlib import Path
from datetime import datetime

class AudiobookTracker:
    """Tracks audiobooks and manages cleanup of orphaned metadata"""
    
    def __init__(self, metadata_dir, covers_dir, media_root):
        self.metadata_dir = Path(metadata_dir)
        self.covers_dir = Path(covers_dir)
        self.media_root = Path(media_root)
        self.summary_file = self.metadata_dir / 'tracking_summary.json'
        
    def load_summary(self):
        """Load the tracking summary file"""
        if self.summary_file.exists():
            with open(self.summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'last_scan': None,
            'tracked_folders': {},
            'tracked_files': {},
            'audiobook_count': 0,
            'created': datetime.now().isoformat()
        }
    
    def save_summary(self, summary):
        """Save the tracking summary file"""
        summary['last_updated'] = datetime.now().isoformat()
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def get_current_file_structure(self):
        """Get current file structure from media directory"""
        current_folders = {}
        current_files = set()
        
        for root, dirs, files in os.walk(self.media_root):
            folder_path = Path(root)
            audio_files = [f for f in files if Path(f).suffix.lower() in ['.mp3', '.m4b', '.flac', '.aac', '.ogg', '.wav']]
            
            if audio_files:
                folder_key = str(folder_path.relative_to(self.media_root))
                current_folders[folder_key] = {
                    'files': audio_files,
                    'file_count': len(audio_files),
                    'last_modified': max(
                        os.path.getmtime(folder_path / f) for f in audio_files
                    )
                }
                
                # Track individual files
                for file in audio_files:
                    file_path = folder_path / file
                    current_files.add(str(file_path.relative_to(self.media_root)))
        
        return current_folders, current_files
    
    def find_orphaned_metadata(self):
        """Find metadata files that no longer have corresponding audio files, are not tracked, or are duplicates"""
        summary = self.load_summary()
        current_folders, current_files = self.get_current_file_structure()
        tracked_folders = summary.get('tracked_folders', {})
        
        orphaned_metadata = []
        orphaned_covers = []
        
        # Group metadata files by folder to detect duplicates
        folder_metadata_map = {}
        
        # Check all metadata files
        for metadata_file in self.metadata_dir.glob('*.json'):
            if metadata_file.name == 'tracking_summary.json':
                continue
                
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                is_orphaned = False
                paths = metadata.get('original', {}).get('paths', [])
                
                if not paths:
                    # No paths means invalid metadata
                    is_orphaned = True
                else:
                    # Check if any of the paths in this metadata still exist
                    paths_exist = False
                    folder_is_tracked = False
                    primary_folder = None
                    
                    for path in paths:
                        # Normalize path separators for comparison
                        normalized_path = path.replace('/', '\\')
                        if normalized_path in current_files:
                            paths_exist = True
                        
                        # Get the primary folder for this metadata (folder name only, not full path)
                        folder_path = str(Path(path).parent)
                        if primary_folder is None:
                            primary_folder = folder_path
                        
                        # Check if the folder containing this file is tracked
                        if folder_path in tracked_folders:
                            folder_is_tracked = True
                    
                    # Mark as orphaned if:
                    # 1. No audio files exist anymore, OR
                    # 2. None of the folders are tracked in our summary
                    if not paths_exist or not folder_is_tracked:
                        is_orphaned = True
                    else:
                        # Check for duplicates - group by primary folder
                        if primary_folder not in folder_metadata_map:
                            folder_metadata_map[primary_folder] = []
                        
                        folder_metadata_map[primary_folder].append({
                            'file': metadata_file,
                            'metadata': metadata,
                            'modified_time': metadata_file.stat().st_mtime
                        })
                
                if is_orphaned:
                    orphaned_metadata.append({
                        'metadata_file': metadata_file,
                        'uuid': metadata.get('original', {}).get('uuid', ''),
                        'title': metadata.get('original', {}).get('title', ''),
                        'paths': metadata.get('original', {}).get('paths', [])
                    })
                    
                    # Check for corresponding cover file
                    cover_image = metadata.get('original', {}).get('coverImage', '')
                    if cover_image and cover_image.startswith('/covers/'):
                        cover_filename = cover_image.replace('/covers/', '')
                        cover_path = self.covers_dir / cover_filename
                        if cover_path.exists():
                            orphaned_covers.append(cover_path)
                            
            except Exception as e:
                print(f"Error checking metadata file {metadata_file}: {e}")
        
        # Handle duplicates - keep only the most recent metadata file per folder
        for folder_path, metadata_list in folder_metadata_map.items():
            if len(metadata_list) > 1:
                # Sort by modification time, keep the newest
                metadata_list.sort(key=lambda x: x['modified_time'], reverse=True)
                newest = metadata_list[0]
                
                # Mark all others as orphaned
                for duplicate in metadata_list[1:]:
                    metadata_file = duplicate['file']
                    metadata = duplicate['metadata']
                    
                    orphaned_metadata.append({
                        'metadata_file': metadata_file,
                        'uuid': metadata.get('original', {}).get('uuid', ''),
                        'title': metadata.get('original', {}).get('title', ''),
                        'paths': metadata.get('original', {}).get('paths', []),
                        'reason': 'duplicate'
                    })
                    
                    # Check for corresponding cover file
                    cover_image = metadata.get('original', {}).get('coverImage', '')
                    if cover_image and cover_image.startswith('/covers/'):
                        cover_filename = cover_image.replace('/covers/', '')
                        cover_path = self.covers_dir / cover_filename
                        if cover_path.exists():
                            orphaned_covers.append(cover_path)
        
        # Find orphaned covers that don't have corresponding metadata files
        active_metadata_uuids = set()
        for metadata_file in self.metadata_dir.glob('*.json'):
            if metadata_file.name == 'tracking_summary.json':
                continue
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    uuid = metadata.get('original', {}).get('uuid', '')
                    if uuid:
                        active_metadata_uuids.add(uuid)
            except Exception:
                continue
        
        # Check all cover files
        for cover_file in self.covers_dir.glob('*.*'):
            cover_uuid = cover_file.stem  # filename without extension
            if cover_uuid not in active_metadata_uuids:
                # This cover doesn't have corresponding metadata
                if cover_file not in orphaned_covers:  # Avoid duplicates
                    orphaned_covers.append(cover_file)
        
        return orphaned_metadata, orphaned_covers
    
    def cleanup_orphaned_data(self, dry_run=True):
        """Remove orphaned metadata and cover files"""
        orphaned_metadata, orphaned_covers = self.find_orphaned_metadata()
        
        cleanup_report = {
            'orphaned_metadata_count': len(orphaned_metadata),
            'orphaned_covers_count': len(orphaned_covers),
            'cleaned_items': [],
            'dry_run': dry_run
        }
        
        if dry_run:
            print(f"DRY RUN: Would remove {len(orphaned_metadata)} metadata files and {len(orphaned_covers)} cover files")
            for item in orphaned_metadata:
                print(f"  Would remove: {item['title']} ({item['metadata_file'].name})")
        else:
            # Actually remove the files
            for item in orphaned_metadata:
                try:
                    item['metadata_file'].unlink()
                    cleanup_report['cleaned_items'].append({
                        'type': 'metadata',
                        'file': str(item['metadata_file']),
                        'title': item['title']
                    })
                    print(f"Removed orphaned metadata: {item['title']}")
                except Exception as e:
                    print(f"Error removing {item['metadata_file']}: {e}")
            
            for cover_file in orphaned_covers:
                try:
                    cover_file.unlink()
                    cleanup_report['cleaned_items'].append({
                        'type': 'cover',
                        'file': str(cover_file)
                    })
                    print(f"Removed orphaned cover: {cover_file.name}")
                except Exception as e:
                    print(f"Error removing {cover_file}: {e}")
        
        return cleanup_report
    
    def update_tracking_after_scan(self, processed_count):
        """Update tracking summary after a scan"""
        summary = self.load_summary()
        current_folders, current_files = self.get_current_file_structure()
        
        # Count actual audiobooks (metadata files excluding tracking_summary.json)
        metadata_files = [f for f in self.metadata_dir.glob('*.json') 
                         if f.name != 'tracking_summary.json']
        total_audiobooks = len(metadata_files)
        
        summary.update({
            'last_scan': datetime.now().isoformat(),
            'tracked_folders': current_folders,
            'tracked_files': list(current_files),
            'audiobook_count': total_audiobooks,  # Total count, not just processed
            'total_audio_files': len(current_files),
            'last_processed_count': processed_count  # Keep track of what was processed this scan
        })
        
        self.save_summary(summary)
        return summary
    
    def get_scan_report(self):
        """Generate a report on current tracking status"""
        summary = self.load_summary()
        current_folders, current_files = self.get_current_file_structure()
        orphaned_metadata, orphaned_covers = self.find_orphaned_metadata()
        
        return {
            'last_scan': summary.get('last_scan'),
            'audiobooks_tracked': summary.get('audiobook_count', 0),
            'current_audio_files': len(current_files),
            'current_folders': len(current_folders),
            'orphaned_metadata': len(orphaned_metadata),
            'orphaned_covers': len(orphaned_covers),
            'needs_cleanup': len(orphaned_metadata) > 0 or len(orphaned_covers) > 0
        }

    def get_folders_to_scan(self):
        """Determine which folders need scanning (new or changed folders only)"""
        summary = self.load_summary()
        tracked_folders = summary.get('tracked_folders', {})
        current_folders, current_files = self.get_current_file_structure()
        
        folders_to_scan = []
        
        for folder_key, folder_info in current_folders.items():
            current_modified = folder_info['last_modified']
            current_count = folder_info['file_count']
            
            # Check if folder is new or changed
            if folder_key in tracked_folders:
                tracked_modified = tracked_folders[folder_key].get('last_modified', 0)
                tracked_count = tracked_folders[folder_key].get('file_count', 0)
                
                # Scan if modified time changed or file count changed
                if (current_modified > tracked_modified or 
                    current_count != tracked_count):
                    folders_to_scan.append(folder_key)
            else:
                # New folder - needs scanning
                folders_to_scan.append(folder_key)
        
        return folders_to_scan, current_folders
