# Configuration settings for the Audiobook Organizer Backend

import os
from pathlib import Path

# Media directories
MEDIA_ROOT = os.getenv('MEDIA_ROOT', 'Z:/Media')
DEST_ROOT = os.getenv('DEST_ROOT', 'Z:/sorted')

# Data directories
METADATA_DIR = Path('./metadata')
COVERS_DIR = Path('./covers')

# Audio file extensions
AUDIO_EXTENSIONS = ['.mp3', '.m4b', '.flac', '.aac', '.ogg', '.wav']

# Status options
STATUS_OPTIONS = ['pending', 'accepted', 'ignored', 'broken', 'manual']

# Server settings
HOST = '0.0.0.0'
PORT = 4000
DEBUG = True

# File processing settings
BATCH_SIZE = 20  # Process groups when they reach this size
SCAN_DELAY = 5   # Seconds to wait before rescanning after file changes
