#!/usr/bin/env python3

import sys
sys.path.append('.')
from audible_service import AudibleSearchService
from pathlib import Path
import json

# Initialize service
service = AudibleSearchService(Path('./covers'))

# Test metadata
test_metadata = {
    'title': 'The Eye of the World',
    'author': 'Robert Jordan',
    'runtime_length_min': 1797,
    'paths': ['test.mp3']
}

print("Testing ID system...")

# Enhance with Audible
result = service.enhance_audiobook_metadata(test_metadata, 'test-uuid')

# Print first suggestion to see ID
if result.get('audible_suggestions'):
    first_suggestion = result['audible_suggestions'][0]
    print(f"First suggestion ID: {first_suggestion.get('id', 'No ID')}")
    print(f"Selected ID: {result.get('selected_audible_id', 'No selected ID')}")
    print(f"Total suggestions: {len(result['audible_suggestions'])}")
    
    # Show all IDs
    print("\nAll suggestions:")
    for i, sugg in enumerate(result['audible_suggestions'][:5]):
        title = sugg.get('title', '')[:50] + ('...' if len(sugg.get('title', '')) > 50 else '')
        print(f"  Suggestion {i+1}: ID={sugg.get('id')}, Title='{title}'")
else:
    print('No suggestions found')
