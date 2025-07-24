# Audiobook Organizer Backend

This backend service watches a folder for new/changed audio files, extracts metadata, and manages audiobook status and organization.

## Status Possibilities
- `pending`: Awaiting user review or action
- `accepted`: User has accepted the suggested metadata
- `ignored`: User has skipped this item
- `broken`: File or metadata is invalid or cannot be processed
- `manual`: User has triggered a manual search or override

## Features (MVP)
- Watches a folder for new/changed audio files
- Extracts metadata (or infers/transcribes if needed)
- Saves results to a data file
- Exposes REST API for listing, updating, and applying status/actions

## Planned
- Audible search and options
- File organization and metadata update on apply
- Integration with frontend UI
