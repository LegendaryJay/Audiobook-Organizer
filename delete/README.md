# Archived Files

This folder contains files that were moved out of the main project structure to keep it organized. These files are not deleted in case they're needed for reference later.

## Files Moved

### `/scripts/` (entire directory removed)
- `dump_audible_metadata.py` - One-time utility for dumping Audible metadata
- `fetch_audible_metadata.py` - One-time script for fetching and enriching audio data

### `/backend/`
- `debug_orphan.py` - Debug script for orphan detection testing
- `debug_orphans.py` - Debug script for orphan detection testing
- `migrate_metadata.py` - One-time migration script for metadata format changes
- `test_*.py` (multiple files) - Test scripts used during development:
  - `test_apis.py`
  - `test_audible_integration.py`
  - `test_cover_collision_fix.py`
  - `test_id_system.py`
  - `test_manual_search.py`
  - `test_paths_update.py`
  - `test_tracker.py`
  - `test_transcriber.py`
  - `test_transcription_integration.py`
- `install_and_run.bat` - Windows batch installer (superseded by direct Python execution)
- `install_and_run.sh` - Unix shell installer (superseded by direct Python execution)
- `package.json` - Unused Node.js package configuration
- `TRANSCRIPTION_SUMMARY.md` - Documentation for transcription features

### Root directory
- `transcribe_first_30_seconds.py` - One-time test script for audio transcription
- `test_media/` - Empty directory that was used for testing

## Active Files Remaining

The following files remain in the active project:

### `/backend/` (Core System)
- `app.py` - Main Flask application
- `audible_service.py` - Audible API integration
- `audiobook_tracker.py` - File tracking and metadata management
- `audiobook_transcriber.py` - Audio transcription service
- `book_series_service.py` - Series detection and organization
- `config.py` - Configuration settings
- `file_watcher.py` - Real-time file monitoring
- `metadata_extractor.py` - Audio metadata extraction
- `path_generator.py` - Organized file path generation
- `polling_watcher.py` - Polling-based file watching
- `storage_interface.py` - Storage abstraction layer
- `requirements.txt` - Python dependencies
- `README.md` - Backend documentation

### `/lunar-light/` (Frontend)
- Complete Astro-based web interface

### Root
- `.github/` - GitHub configuration and Copilot instructions
- `.vscode/` - VS Code workspace settings
- `README.md` - Main project documentation
- Configuration files (`.gitignore`)

All archived files can be restored if needed by moving them back to their original locations.
