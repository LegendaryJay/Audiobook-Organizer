#!/usr/bin/env python3

import sys
sys.path.append('.')
from audible_service import AudibleSearchService
from pathlib import Path
import json

# Initialize service
service = AudibleSearchService(Path('./covers'))

# Test metadata - this is the "Restore Me" book
test_metadata = {
    'title': 'Restore Me (Unabridged)',
    'author': 'Tahereh Mafi',
    'runtime_length_min': 519,
    'paths': ['Tahereh Mafi - Restore Me Shatter Me, Book 4 (Unabridged)/Restore Me Shatter Me, Book 4 (Unabridged).m4b']
}

print("Testing paths field population...")

# Enhance with Audible
result = service.enhance_audiobook_metadata(test_metadata, 'test-uuid')

if result.get('audible_suggestions'):
    first_suggestion = result['audible_suggestions'][0]
    print(f"First suggestion ID: {first_suggestion.get('id', 'No ID')}")
    print(f"First suggestion paths: {first_suggestion.get('paths', 'No paths')}")
    print(f"First suggestion organized_paths: {first_suggestion.get('organized_paths', 'No organized_paths')}")
    print(f"Selected ID: {result.get('selected_audible_id', 'No selected ID')}")
else:
    print('No suggestions found')
