# Copilot Instructions for Audiobook Organizer

## Project Overview
This is an audiobook organization and metadata management system with a Python/Flask backend and file-based storage architecture.

## Architecture
- **Backend**: Python/Flask server (`backend/`) with streaming/batch processing
- **File Storage**: UUID-based metadata and cover image files
- **Data Structure**: Each audiobook has `metadata/<uuid>.json` and optional `covers/<uuid>.<ext>`
- **Memory Management**: Streaming/batch processing to handle large audio libraries without memory issues

## Key Components

### Backend Files
- `backend/app.py` - Main Flask server, API endpoints, initialization
- `backend/metadata_extractor.py` - Audio metadata extraction, grouping, file processing
- `backend/file_watcher.py` - File system monitoring using watchdog
- `backend/config.py` - Configuration settings and constants
- `backend/requirements.txt` - Python dependencies

### Data Architecture
```
metadata/
  ├── <uuid1>.json - Individual audiobook metadata
  ├── <uuid2>.json - Individual audiobook metadata
  └── ...
covers/
  ├── <uuid1>.jpg - Cover images extracted from audio files
  ├── <uuid2>.png - Cover images extracted from audio files
  └── ...
```

### Metadata Structure
Each `metadata/<uuid>.json` contains:
```json
{
  "original": {
    "uuid": "generated-uuid",
    "title": "Book Title",
    "author": "Author Name",
    "coverImage": "/covers/uuid.jpg",
    "year": "2023",
    "genre": "Fiction",
    "narrator": "Narrator Name",
    "runtime_length_min": 480,
    "asin": "B123456789",
    "paths": ["/relative/path/to/file1.mp3", "/relative/path/to/file2.mp3"]
  },
  "status": "pending",
  "audible_suggestions": [
    {
      "id": 1,
      "title": "Enhanced Title",
      "author": "Enhanced Author",
      "narrator": "Enhanced Narrator",
      "series": "Series Name",
      "book_number": "1",
      "match_score": 0.95,
      "match_confidence": "high",
      "paths": ["/organized/path/file1.mp3"]
    }
  ],
  "selected_audible_id": 1,
  "audible_last_search": "Auto-enhanced via Audible API"
}
```

**Field Descriptions:**
- `original`: Original metadata extracted from audio files
- `status`: Current processing status ("pending", "accepted", "ignored", "broken", "manual")
- `audible_suggestions`: Array of Audible API enhancement suggestions with sequential IDs
- `selected_audible_id`: ID of the currently selected suggestion (1-based)
- `audible_last_search`: Log of the last Audible search performed

## Coding Guidelines

### Python Style
- **Use Python 3.8+**: Modern Python features and type hints
- **Flask patterns**: Use blueprints for larger applications, proper error handling
- **Memory efficiency**: Use generators and streaming processing for large datasets
- **Exception handling**: Graceful error handling, never crash on single file errors

### Dependencies
- `flask` - Web framework and API server
- `mutagen` - Audio file metadata extraction (more robust than Node.js alternatives)
- `watchdog` - File system monitoring for real-time updates
- `pillow` - Image processing for cover art extraction and optimization
- `flask-cors` - CORS support for frontend communication

### Key Functions
- `process_all_audiobooks()` - Main streaming processor (memory-safe)
- `build_audiobook_metadata()` - Processes and saves single audiobook group
- `extract_cover_image()` - Extracts and saves cover images using Pillow
- `walk_audio_files()` - Generator for recursively finding audio files
- `group_files_by_album()` - Groups audio files by album/artist

### Path Generator (`backend/path_generator.py`)
The path generator creates standardized file organization structures based on Audible metadata.

**Key Functions:**
- `generate_paths_for_audiobook(audiobook_data, suggestion_index)` - Main function that generates organized paths
- `preview_organization(audiobook_data, suggestion_index)` - Creates human-readable preview text
- `sanitize_filename(text)` - Safely formats text for use in file/folder names

**Organization Format:**
```
{Series Title}/{Book Number}-{Book Title} ({Release Year})/
├── {Book Title}.mp3                          (single file)
└── {Book Title} [Part XX].mp3               (multi-part)
```

**Usage Pattern:**
```python
from path_generator import generate_paths_for_audiobook, preview_organization

# Generate organized paths
result = generate_paths_for_audiobook(audiobook_data, selected_suggestion_index)
if result:
    organized_paths = result['organized_paths']  # List of new file paths
    folder_structure = result['folder_structure']  # Metadata about folders
    original_paths = result['original_paths']  # Reference to source files

# Generate preview text
preview_text = preview_organization(audiobook_data, selected_suggestion_index)
```

**Path Generation Result Structure:**
```python
{
    'organized_paths': ['/Series/01-Title (2023)/Title [Part 01].mp3'],
    'folder_structure': {
        'series_folder': 'Series Name',
        'book_folder': '01-Title (2023)',
        'full_folder_path': 'Series Name/01-Title (2023)',
        'is_multi_part': True,
        'part_count': 12
    },
    'original_paths': ['/original/path/file1.mp3'],
    'selected_suggestion': {...},  # The Audible suggestion used
    'suggestion_index': 0
}
```

**Integration Points:**
- Called by `/api/audiobooks/<uuid>/paths` endpoint for path generation
- Called by `/api/audiobooks/<uuid>/preview` endpoint for organization preview  
- Called by manual search to populate `paths` field in suggestions
- Called by regular Audible enhancement to populate `paths` field in suggestions
- Uses `selected_audible_id` from metadata to determine which suggestion to use

**Path Integration Requirements:**
- After fetching from Audible (both manual search and regular enhancement), generated paths should replace the `paths` field in each suggestion
- The organized paths should be stored in the same `paths` field, not a new data label
- When displayed in the frontend, organized paths should look identical to original paths (no visual distinction)
- Original paths remain in the `original` metadata, while Audible suggestions get organized paths in their `paths` field

### API Endpoints
- `GET /api/audiobooks` - Paginated audiobook listing with offset/limit
- `POST /api/audiobooks/<uuid>/status` - Update audiobook status by UUID
- `POST /api/audiobooks/<int:index>/status` - Legacy index-based status update
- `POST /api/audible/<uuid>` - Enhance audiobook with Audible search
- `POST /api/audiobooks/<uuid>/manual-search` - Manual Audible search with custom query
- `POST /api/audiobooks/<uuid>/select-audible` - Update selected Audible suggestion
- `POST /api/audiobooks/<uuid>/paths` - Generate organized file paths
- `POST /api/audiobooks/<uuid>/preview` - Preview audiobook organization
- `POST /api/scan` - Manual rescan trigger
- `POST /api/purge` - Delete all data and regenerate from scratch
- `GET /covers/:filename` - Serve cover images with proper headers

### File Paths
- Source: `Z:/Media` (configurable via environment)
- Metadata: `./metadata/`
- Covers: `./covers/`
- Destination: `Z:/sorted` (for organized files)

## Common Patterns

### Error Handling
```python
try:
    audio_file = File(str(file_path))
    if not audio_file:
        continue  # Skip invalid files
    # process audio_file
except Exception as e:
    print(f"Error processing {file_path}: {e}")
    continue  # Don't crash, just skip problematic files
```

### Memory-Safe Processing
```python
# Good: Process and save immediately using generators
for file_path in walk_audio_files(media_root):
    # Process one file at a time
    process_file(file_path)
    # File data is garbage collected automatically

# Bad: Loading everything into memory
all_files = list(walk_audio_files(media_root))  # Loads all paths into memory
```

### UUID-Based File Operations
```python
import uuid
from pathlib import Path

audiobook_uuid = str(uuid.uuid4())
metadata_file = METADATA_DIR / f"{audiobook_uuid}.json"
cover_file = COVERS_DIR / f"{audiobook_uuid}.{ext}"
```

### Flask Route Patterns
```python
@app.route('/api/audiobooks')
def get_audiobooks():
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 10))
        # ... processing
        return jsonify({'total': total, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Status Values
- `pending` - New, needs user review
- `accepted` - User approved metadata
- `ignored` - User wants to skip
- `broken` - Has issues
- `manual` - Needs manual intervention

## Performance Considerations
- Large libraries (10k+ audiobooks) must use streaming processing with generators
- Cover images are stored separately, never embedded in JSON
- Use file watching for incremental updates, not full rescans
- Batch operations to avoid overwhelming the file system
- Python's `mutagen` library is more memory-efficient than JavaScript alternatives

## Future Enhancements
- Audible API integration for enhanced metadata
- Audio transcription using `speech_recognition` library
- Automated file organization and renaming with proper backup
- Web frontend for user curation interface
- Machine learning for automated metadata inference

## Development Notes
- Always test with large audio libraries to ensure memory efficiency
- Use `pathlib.Path` for cross-platform file operations
- Handle Windows/Unix path separators correctly
- Gracefully handle corrupted or inaccessible audio files
- Use proper logging instead of print statements in production
- Consider using async/await for I/O heavy operations in future versions
