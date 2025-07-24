
# Audiobook Organizer
## Vision

This project aims to provide a fully automated and user-guided audiobook organizer with the following workflow:

- **Backend Service**: Runs on a server and watches a folder for new or changed audio files.
- **Automatic Metadata Extraction**:
  - On detecting a new audio file, the backend will:
    1. Attempt to extract metadata from the file.
    2. If metadata is missing, infer details from the file/folder structure.
    3. If that fails, transcribe the first 2 minutes of audio and save the transcript in the data.
- **Audible Search & Options**:
  - Uses the gathered metadata to search Audible and saves the most relevant results under an `options` field.
  - Displays the Audible metadata it thinks is the best match under `new`.
- **User Curation**:
  - The user is required to select the most relevant Audible data from the options.
  - An "Apply" button tells the server to organize the files accordingly.
- **File Organization & Metadata Update**:
  - On apply, the backend:
    - Adds a `backup` metadata field to the file, saving any metadata that is changed (not just a copy of `old`).
    - Renames and moves the file to a specific location.
    - Updates file metadata (cover, title, author, etc.) as chosen by the user.


A modern web-based tool for organizing, enriching, and browsing your audiobook collection. Built with Python/Flask backend and file-based storage architecture.

## Features
- **Memory-Efficient Processing**: Handles large audiobook libraries without memory issues
- **Robust Metadata Extraction**: Uses Python's `mutagen` library for comprehensive audio metadata
- **UUID-Based Storage**: Each audiobook stored as individual metadata and cover files
- **Real-time File Watching**: Automatically detects new audiobooks added to library
- **REST API**: Clean API for frontend integration
- **Cover Image Extraction**: Automatically extracts and serves cover art
- **Status Management**: Track audiobook processing status (pending, accepted, ignored, etc.)
- **Streaming Processing**: Never loads entire library into memory
- **Pagination Support**: Frontend displays audiobooks in pages (configurable: 10, 25, 50, 100 per page)
- **Audible Integration**: Search and enhance metadata using Audible data
- **File Organization**: Automated file organization with configurable destination paths

## Architecture
- **Backend**: Python/Flask server with file-based storage
- **Data Storage**: UUID-based individual files for metadata and covers
- **Memory Management**: Streaming/batch processing for large libraries
- **File Watching**: Automatic detection of library changes

## Project Structure
```
backend/
├── app.py                    # Main Flask application
├── metadata_extractor.py     # Audio metadata extraction and processing
├── file_watcher.py          # File system monitoring
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
```

## Setup

### Python Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
1. **Install dependencies**
   ```sh
   cd lunar-light
   npm install
   ```
2. **Run the development server**
   ```sh
   npx astro dev
   ```
3. **Access the app**
   Open [http://localhost:4321](http://localhost:4321) in your browser.

## API Endpoints

- `GET /api/audiobooks` - Get paginated list of audiobooks (supports `?offset=X&limit=Y`)
- `POST /api/audiobooks/:uuid/status` - Update audiobook status  
- `POST /api/organize` - Copy/move accepted audiobooks to organized folder structure
- `POST /api/scan` - Trigger manual library scan
- `GET /covers/:filename` - Serve cover images

## Dependencies

### Python Backend
- **Flask**: Web framework
- **mutagen**: Audio metadata extraction
- **watchdog**: File system monitoring
- **Pillow**: Image processing for covers
- **flask-cors**: CORS support for frontend

## Data Structure

Each audiobook is stored as:
- `metadata/<uuid>.json` - Metadata and file paths
- `covers/<uuid>.<ext>` - Extracted cover image (if available)

### Metadata Format
```json
{
  "old": {
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
  "new": {},
  "status": "pending"
}
```

## Memory Efficiency

The backend uses streaming processing to handle large libraries:
- Processes files in batches
- Saves metadata immediately after extraction
- Never loads entire library into memory
- Suitable for libraries with 10,000+ audiobooks

## Future Enhancements
- Audible API integration for enhanced metadata
- Audio transcription for metadata inference  
- Automated file organization and renaming
- Web frontend for user curation interface

## License
MIT
