
# Audiobook Organizer

A modern web-based tool for organizing, enriching, and browsing your audiobook collection. Built with Python/Flask backend and Astro frontend with real-time updates.

## Features
- **Memory-Efficient Processing**: Handles large audiobook libraries without memory issues
- **Robust Metadata Extraction**: Uses Python's `mutagen` library for comprehensive audio metadata
- **UUID-Based Storage**: Each audiobook stored as individual metadata and cover files
- **Real-time Updates**: Server-Sent Events (SSE) for live frontend updates without page refresh
- **File Organization**: Move (not copy) accepted audiobooks to organized folder structure
- **Audible Integration**: Search and enhance metadata using Audible data with manual search capability
- **Cover Image Extraction**: Automatically extracts and serves cover art
- **Status Management**: Track audiobook processing status (pending, accepted, ignored, broken, manual)
- **Streaming Processing**: Never loads entire library into memory
- **Pagination Support**: Frontend displays audiobooks in pages (configurable: 10, 25, 50, 100 per page)
- **File Path Generation**: Automatically generates organized paths with preview functionality
- **Comprehensive API**: REST endpoints for all audiobook operations

## Architecture
- **Backend**: Python/Flask server with file-based storage and SSE support
- **Frontend**: Astro-based web interface with real-time updates
- **Data Storage**: UUID-based individual files for metadata and covers
- **Memory Management**: Streaming/batch processing for large libraries
- **Real-time Communication**: Server-Sent Events for live updates

## Project Structure
```
backend/
├── app.py                    # Main Flask application with SSE support
├── metadata_extractor.py     # Audio metadata extraction and processing
├── file_watcher.py          # File system monitoring
├── path_generator.py        # Organized path generation system
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── metadata/              # Individual audiobook metadata files
│   ├── <uuid1>.json
│   ├── <uuid2>.json
│   └── ...
└── covers/               # Extracted cover images
    ├── <uuid1>.jpg
    ├── <uuid2>.png
    └── ...

lunar-light/                 # Astro frontend
├── src/
│   ├── components/
│   │   ├── AudioList.astro  # Main audiobook list with SSE integration
│   │   └── AudioCard.astro  # Individual audiobook cards
│   ├── pages/
│   │   └── index.astro     # Main page with organize functionality
│   └── ...
└── ...
```

## Setup

### Python Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
The backend will run on `http://localhost:4000`

### Astro Frontend
```bash
cd lunar-light
npm install
npx astro dev
```
The frontend will run on `http://localhost:4321`

### Configuration
- Source library: `Z:/Media` (configurable via environment)
- Organized destination: `Z:/MediaSorted`
- Metadata storage: `./metadata/`
- Cover storage: `./covers/`

## API Endpoints

### Core Operations
- `GET /api/audiobooks` - Get paginated list of audiobooks (supports `?offset=X&limit=Y`)
- `POST /api/audiobooks/<uuid>/status` - Update audiobook status by UUID
- `POST /api/organize` - Move accepted audiobooks to organized folder structure
- `POST /api/scan` - Trigger manual library scan
- `POST /api/purge` - Delete all data and regenerate from scratch
- `GET /covers/<filename>` - Serve cover images

### Audible Integration
- `POST /api/audible/<uuid>` - Enhance audiobook with Audible search
- `POST /api/audiobooks/<uuid>/manual-search` - Manual Audible search with custom query
- `POST /api/audiobooks/<uuid>/select-audible` - Update selected Audible suggestion

### Path Generation
- `POST /api/audiobooks/<uuid>/paths` - Generate organized file paths
- `POST /api/audiobooks/<uuid>/preview` - Preview audiobook organization

### Real-time Updates
- `GET /api/events` - Server-Sent Events stream for real-time updates

## Dependencies

### Python Backend
- **Flask**: Web framework and API server
- **mutagen**: Audio metadata extraction
- **watchdog**: File system monitoring
- **Pillow**: Image processing for covers
- **flask-cors**: CORS support for frontend

### Frontend
- **Astro**: Modern web framework for fast static sites
- **JavaScript**: Real-time SSE communication and DOM manipulation

## Data Structure

Each audiobook is stored as:
- `metadata/<uuid>.json` - Metadata and file paths
- `covers/<uuid>.<ext>` - Extracted cover image (if available)

### Metadata Format
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
    "paths": ["/relative/path/to/file1.mp3"]
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

### Status Values
- `pending` - New, needs user review
- `accepted` - User approved metadata, ready for organization
- `ignored` - User wants to skip
- `broken` - Has issues that need resolution
- `manual` - Needs manual intervention

## File Organization

Audiobooks are organized using the following structure:
```
{Author}/{Series}/{BookNumber}-{Title} ({Year})/
├── {Title}.mp3                          (single file)
└── {Title} [Part XX].mp3               (multi-part)
```

Example:
```
J.K. Rowling/Harry Potter/01-Harry Potter and the Philosopher's Stone (1997)/
├── Harry Potter and the Philosopher's Stone [Part 01].mp3
├── Harry Potter and the Philosopher's Stone [Part 02].mp3
└── ...
```

## Real-time Updates

The system uses Server-Sent Events (SSE) to provide real-time updates:

### Event Types
- `status_update` - When audiobook status changes
- `scan_complete` - When library scan finishes
- `purge_complete` - When data purge completes
- `organize_complete` - When file organization finishes

### Frontend Integration
The Astro frontend automatically:
- Connects to SSE stream on page load
- Updates audiobook list without page refresh
- Shows real-time status changes
- Handles organize operations with immediate feedback

## Memory Efficiency

The backend uses streaming processing to handle large libraries:
- Processes files in batches
- Saves metadata immediately after extraction
- Never loads entire library into memory
- Suitable for libraries with 10,000+ audiobooks
- Cleanup operations remove metadata and covers for moved files

## Usage Workflow

1. **Start the backend**: `python app.py` from the backend directory
2. **Start the frontend**: `npx astro dev` from the lunar-light directory
3. **Initial scan**: The system automatically scans for audiobooks on startup
4. **Review audiobooks**: 
   - View audiobooks in the web interface
   - See original metadata vs. Audible suggestions
   - Use manual search for better matches if needed
5. **Accept or skip**: Mark audiobooks as accepted (will be organized) or ignored
6. **Organize**: Click "Organize Accepted" to move files to organized structure
7. **Real-time updates**: All changes reflect immediately without page refresh

## Future Enhancements
- Audio transcription for metadata inference when file tags are missing
- Automated file watching for continuous monitoring
- Advanced search and filtering options
- Batch operations for multiple audiobooks
- Export/import functionality for metadata
- Integration with additional metadata sources

## License
MIT
