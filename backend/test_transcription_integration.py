"""
Test script showing how transcription can be integrated with the audible service
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from audiobook_transcriber import get_transcription_metadata
from audible_service import AudibleSearchService
import json

def test_transcription_integration():
    """Test how transcription can supplement Audible search"""
    
    # Test folder
    test_folder = "Z:/Media/Book 8 - Mark of the Fool"
    
    print("=== TRANSCRIPTION-BASED METADATA EXTRACTION ===")
    
    # Get transcription metadata
    transcription_result = get_transcription_metadata(test_folder)
    
    if transcription_result['transcription_available']:
        transcription_meta = transcription_result['transcription_metadata']
        
        print(f"Title: {transcription_meta['title']}")
        print(f"Author: {transcription_meta['author']}")
        print(f"Narrator: {transcription_meta['narrator']}")
        print(f"Publisher: {transcription_meta['publisher']}")
        print(f"Platform: {transcription_meta['platform']}")
        
        print(f"\nTranscription source: {transcription_result['transcription_source']['source']}")
        print(f"Source file: {transcription_result['transcription_source']['file']}")
        
        # Show how this could be used to search Audible
        print("\n=== USING TRANSCRIPTION FOR AUDIBLE SEARCH ===")
        
        # Create search query from transcription metadata
        search_query = {
            'title': transcription_meta['title'],
            'author': transcription_meta['author'],
            'filename': transcription_result['transcription_source']['file']
        }
        
        print("Search query from transcription:")
        print(json.dumps(search_query, indent=2))
        
        # You could now use this with AudibleSearchService:
        # audible_service = AudibleSearchService("Z:/Audiobook Organizer/covers")
        # results = audible_service.search_audible(search_query)
        
        print("\n=== METADATA COMPARISON POSSIBILITIES ===")
        print("The transcription metadata could be used to:")
        print("1. Search Audible when file metadata is missing")
        print("2. Verify/enhance existing metadata")
        print("3. Provide fallback when Audible search fails")
        print("4. Extract narrator information often missing from tags")
        
    else:
        print(f"Transcription failed: {transcription_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_transcription_integration()
