import os
import json
import uuid
from pathlib import Path
from mutagen._file import File
from PIL import Image
import io
import re
from audible_service import AudibleSearchService

# Configuration
AUDIO_EXTENSIONS = ['.mp3', '.m4b', '.flac', '.aac', '.ogg', '.wav']
METADATA_DIR = Path('./metadata')
COVERS_DIR = Path('./covers')
DEST_ROOT = 'Z:/sorted'

# Ensure directories exist
METADATA_DIR.mkdir(exist_ok=True)
COVERS_DIR.mkdir(exist_ok=True)

def is_audio_file(filename):
    """Check if file is an audio file"""
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS

def walk_audio_files(directory):
    """Generator to walk through all audio files in directory"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if is_audio_file(file):
                yield Path(root) / file

def extract_tag(audio_file, tag_name):
    """Extract a tag value from audio file"""
    if not audio_file:
        return ''
    
    # Handle different tag formats
    tag_mappings = {
        'title': ['TIT2', 'TITLE', '\xa9nam'],
        'artist': ['TPE1', 'ARTIST', '\xa9ART'],
        'album': ['TALB', 'ALBUM', '\xa9alb'],
        'year': ['TDRC', 'DATE', '\xa9day'],
        'genre': ['TCON', 'GENRE', '\xa9gen'],
        'track': ['TRCK', 'TRACKNUMBER', 'trkn'],
        'narrator': ['TPE3', 'PERFORMER', 'NARRATOR'],
        'asin': ['TXXX:ASIN', 'ASIN']
    }
    
    possible_tags = tag_mappings.get(tag_name, [tag_name.upper()])
    
    for tag in possible_tags:
        if tag in audio_file:
            value = audio_file[tag]
            if isinstance(value, list) and value:
                return str(value[0])
            elif value:
                return str(value)
    
    return ''

def get_track_number(audio_file):
    """Extract track number from audio file"""
    if not audio_file:
        return 0
    
    track = extract_tag(audio_file, 'track')
    if track:
        # Handle "1/12" format
        if '/' in track:
            track = track.split('/')[0]
        try:
            return int(track)
        except ValueError:
            return 0
    return 0

def extract_cover_image(audio_file, uuid_str):
    """Extract and save cover image from audio file"""
    if not audio_file:
        return ''
    
    # Try to get cover art
    artwork = None
    
    # ID3 tags (MP3)
    if hasattr(audio_file, 'tags') and audio_file.tags:
        for key in audio_file.tags:
            if key.startswith('APIC'):
                artwork = audio_file.tags[key].data
                break
    
    # MP4 tags
    if 'covr' in audio_file:
        artwork = audio_file['covr'][0]
    
    if not artwork:
        return ''
    
    try:
        # Determine image format
        image = Image.open(io.BytesIO(artwork))
        format_ext = image.format.lower() if image.format else 'jpg'
        
        filename = f"{uuid_str}.{format_ext}"
        cover_path = COVERS_DIR / filename
        
        # Save cover image
        with open(cover_path, 'wb') as f:
            f.write(artwork)
        
        return filename
    
    except Exception as e:
        print(f"Error extracting cover: {e}")
        return ''

def group_files_by_folder(files_with_metadata):
    """Group files by their parent folder - assumes all files in same folder = same audiobook"""
    groups = {}
    
    for file_path, audio_file in files_with_metadata:
        # Use the parent folder as the grouping key
        folder_key = str(file_path.parent)
        
        if folder_key not in groups:
            groups[folder_key] = []
        
        groups[folder_key].append((file_path, audio_file))
    
    return groups

def build_audiobook_metadata(files_group, media_root=None):
    """Build metadata for a group of audio files (one audiobook) with Audible enhancement"""
    if media_root is None:
        media_root = 'Z:/Media'  # Default fallback
    
    # Sort by track number
    files_group.sort(key=lambda x: get_track_number(x[1]))
    
    # Get metadata from first file with tags
    first_file_path, first_audio = next(((f, a) for f, a in files_group if a), (files_group[0][0], None))
    
    # Calculate total duration
    total_duration = 0
    for file_path, audio_file in files_group:
        if audio_file and hasattr(audio_file, 'info') and audio_file.info.length:
            total_duration += audio_file.info.length
    
    # Extract narrator from comments or performer
    narrator = extract_tag(first_audio, 'narrator')
    if not narrator and first_audio:
        # Check comments for narrator info
        comments = extract_tag(first_audio, 'COMM::eng') or extract_tag(first_audio, 'comment')
        if 'narrat' in comments.lower():
            narrator = comments
    
    # Extract ASIN
    asin = extract_tag(first_audio, 'asin')
    if not asin and first_audio:
        # Check comments for ASIN
        comments = extract_tag(first_audio, 'COMM::eng') or extract_tag(first_audio, 'comment')
        import re
        asin_match = re.search(r'asin[:= ]?([A-Z0-9]{10})', comments, re.IGNORECASE)
        if asin_match:
            asin = asin_match.group(1)
    
    # Generate UUID
    audiobook_uuid = str(uuid.uuid4())
    
    # Extract and save cover image
    cover_filename = extract_cover_image(first_audio, audiobook_uuid)
    
    # Build original metadata
    original_metadata = {
        'uuid': audiobook_uuid,
        'title': extract_tag(first_audio, 'album') or extract_tag(first_audio, 'title') or first_file_path.parent.name,
        'author': extract_tag(first_audio, 'artist'),
        'coverImage': f'/covers/{cover_filename}' if cover_filename else '',
        'year': extract_tag(first_audio, 'year'),
        'genre': extract_tag(first_audio, 'genre'),
        'narrator': narrator,
        'runtime_length_min': int(total_duration / 60) if total_duration else 0,
        'asin': asin,
        'paths': [
            str(file_path.relative_to(Path(media_root))).replace('\\', '/')
            for file_path, _ in files_group
        ]
    }
    
    # Initialize Audible service and search for enhanced metadata
    print(f"[AUDIBLE] Enhancing metadata for: {original_metadata['title']}")
    audible_service = AudibleSearchService(COVERS_DIR)
    
    try:
        audible_enhancement = audible_service.enhance_audiobook_metadata(original_metadata, audiobook_uuid)
        audible_suggestions = audible_enhancement.get('audible_suggestions', [])
        print(f"[AUDIBLE] Found {len(audible_suggestions)} suggestions")
    except Exception as e:
        print(f"[AUDIBLE ERROR] Failed to enhance metadata: {e}")
        audible_suggestions = []
    
    # Save metadata to file with new structure
    metadata_file = METADATA_DIR / f"{audiobook_uuid}.json"
    audiobook_data = {
        'original': original_metadata,
        'audible_suggestions': audible_suggestions,
        'status': 'pending'
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(audiobook_data, f, indent=2, ensure_ascii=False)
    
    return audiobook_data

def process_all_audiobooks(media_root):
    """
    Memory-efficient processing: stream through files, group by folder, and save immediately
    """
    print(f"Scanning audio files in {media_root}...")
    
    folder_groups = {}
    processed_count = 0
    total_files_found = 0
    
    for file_path in walk_audio_files(media_root):
        total_files_found += 1
        try:
            # Load audio file metadata
            audio_file = File(str(file_path))
            if not audio_file:
                print(f"Warning: Could not parse audio file: {file_path}")
                continue
            
            # Group by parent folder (much simpler and more reliable)
            folder_key = str(file_path.parent)
            
            if folder_key not in folder_groups:
                folder_groups[folder_key] = []
            
            folder_groups[folder_key].append((file_path, audio_file))
            
            # Don't process early - let each folder accumulate ALL its files first
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"Found {total_files_found} total audio files")
    
    # Process all folder groups at the end (ensures each folder is complete)
    for folder_key in list(folder_groups.keys()):
        try:
            if folder_groups[folder_key]:  # Only process non-empty groups
                folder_name = Path(folder_key).name
                file_count = len(folder_groups[folder_key])
                print(f"Processing folder: {folder_name} ({file_count} files)")
                build_audiobook_metadata(folder_groups[folder_key], media_root)
                processed_count += 1
                del folder_groups[folder_key]  # Free memory
        except Exception as e:
            print(f"Error processing folder {folder_key}: {e}")
    
    print(f"Processed {processed_count} audiobooks")
    return processed_count

def process_specific_folders(media_root, folders_to_scan):
    """
    Process only specific folders that need scanning (new or changed folders)
    """
    if not folders_to_scan:
        print("No folders need scanning - all audiobooks are up to date")
        return 0
        
    print(f"Scanning {len(folders_to_scan)} changed/new folders...")
    
    folder_groups = {}
    processed_count = 0
    total_files_found = 0
    
    # Only walk through the specific folders that need scanning
    for folder_relative_path in folders_to_scan:
        folder_path = Path(media_root) / folder_relative_path
        
        if not folder_path.exists():
            print(f"Warning: Folder {folder_path} no longer exists")
            continue
            
        print(f"Scanning folder: {folder_relative_path}")
        
        # Process all audio files in this specific folder
        for file_path in folder_path.glob('*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.m4b', '.flac', '.aac', '.ogg', '.wav']:
                total_files_found += 1
                try:
                    # Load audio file metadata
                    audio_file = File(str(file_path))
                    if not audio_file:
                        print(f"Warning: Could not parse audio file: {file_path}")
                        continue
                    
                    # Group by parent folder
                    folder_key = str(file_path.parent)
                    
                    if folder_key not in folder_groups:
                        folder_groups[folder_key] = []
                    
                    folder_groups[folder_key].append((file_path, audio_file))
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
    
    print(f"Found {total_files_found} total audio files in changed folders")
    
    # Process the folder groups
    for folder_key in list(folder_groups.keys()):
        try:
            if folder_groups[folder_key]:  # Only process non-empty groups
                folder_name = Path(folder_key).name
                file_count = len(folder_groups[folder_key])
                print(f"Processing folder: {folder_name} ({file_count} files)")
                build_audiobook_metadata(folder_groups[folder_key], media_root)
                processed_count += 1
                del folder_groups[folder_key]  # Free memory
        except Exception as e:
            print(f"Error processing folder {folder_key}: {e}")
    
    print(f"Processed {processed_count} changed audiobooks")
    return processed_count
