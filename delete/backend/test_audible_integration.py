"""
Test script for Audible integration
Tests the enhanced metadata extraction with Audible search
"""

import json
from pathlib import Path
from audible_service import AudibleSearchService

def test_audible_integration():
    """Test the Audible search and enhancement functionality"""
    
    # Test data simulating extracted audiobook metadata
    test_metadata = {
        'title': 'Find Me',
        'author': 'Tahereh Mafi',
        'runtime_length_min': 239,
        'asin': '',  # No ASIN to test search
        'paths': ['Tahereh Mafi - Find Me [Shatter Me, Book 4.5, 5.5]/Tahereh Mafi - Find Me [Shatter Me, Book 4.5, 5.5].mp3']
    }
    
    print("Testing Audible Service Integration")
    print("=" * 50)
    print(f"Original metadata:")
    print(f"  Title: {test_metadata['title']}")
    print(f"  Author: {test_metadata['author']}")
    print(f"  Runtime: {test_metadata['runtime_length_min']} minutes")
    print(f"  ASIN: {test_metadata['asin'] or 'None'}")
    print()
    
    # Initialize service
    covers_dir = Path('./covers')
    service = AudibleSearchService(covers_dir)
    
    # Test the enhancement
    try:
        result = service.enhance_audiobook_metadata(test_metadata, 'test-uuid-12345')
        
        print("Audible Search Results:")
        print(f"  Enhanced: {result.get('audible_enhanced', False)}")
        print(f"  Total results: {result.get('total_results', 0)}")
        print(f"  Message: {result.get('message', 'No message')}")
        print()
        
        suggestions = result.get('audible_suggestions', [])
        if suggestions:
            print(f"Top {min(3, len(suggestions))} suggestions:")
            print("-" * 30)
            
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"{i}. {suggestion.get('title', 'Unknown Title')}")
                print(f"   Author: {suggestion.get('author', 'Unknown')}")
                print(f"   Narrator: {suggestion.get('narrator', 'Unknown')}")
                print(f"   Runtime: {suggestion.get('runtime_length_min', 'Unknown')} min")
                print(f"   ASIN: {suggestion.get('asin', 'Unknown')}")
                print(f"   Match Score: {suggestion.get('match_score', 0.0):.2f}")
                print(f"   Confidence: {suggestion.get('match_confidence', 'unknown')}")
                print(f"   Cover: {suggestion.get('coverImage', 'None')}")
                print(f"   URL: {suggestion.get('audible_url', 'None')}")
                print()
        else:
            print("No suggestions found.")
        
        return result
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return None

def test_without_audible_cli():
    """Test the service when audible CLI is not available"""
    print("Testing fallback behavior (simulated CLI failure)")
    print("=" * 50)
    
    # This will test the error handling when audible CLI is not available
    service = AudibleSearchService(Path('./covers'))
    
    test_metadata = {
        'title': 'Test Book',
        'author': 'Test Author',
        'runtime_length_min': 300
    }
    
    try:
        result = service.enhance_audiobook_metadata(test_metadata, 'test-uuid-67890')
        print(f"Result: {result}")
    except Exception as e:
        print(f"Expected error (CLI not available): {e}")

if __name__ == '__main__':
    # Test with actual metadata
    result = test_audible_integration()
    
    print("\n" + "=" * 50)
    
    # Test error handling
    test_without_audible_cli()
    
    print("\nTest completed!")
