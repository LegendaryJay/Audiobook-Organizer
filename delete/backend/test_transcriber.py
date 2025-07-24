"""
Test script for audiobook transcriber
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from audiobook_transcriber import AudiobookTranscriber
import json

def test_transcriber():
    transcriber = AudiobookTranscriber()
    
    # Check dependencies
    print("=== DEPENDENCY CHECK ===")
    transcriber.check_dependencies()
    
    # Test with a few common paths (you can adjust these)
    test_paths = [
        "Z:/Media",  # Your original media path
        "Z:/Audiobook Organizer/test_media",
        # Add any specific audiobook folder paths you want to test
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            print(f"\n=== TESTING PATH: {path} ===")
            
            # Test structure detection
            structure = transcriber.detect_audiobook_structure(path)
            print(f"Structure: {json.dumps(structure, indent=2, default=str)}")
            
            # If there are audio files, test full transcription
            if structure['type'] != 'no_audio':
                print(f"\nRunning full transcription test...")
                result = transcriber.get_transcription_for_audiobook(path)
                
                print(f"Success: {result['success']}")
                if result['success']:
                    print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
                    print(f"Source: {result['source_info']}")
                    print(f"Transcription preview: {result['transcription'][:200]}...")
                else:
                    print(f"Failed to transcribe")
                
                break  # Only test the first valid path
        else:
            print(f"Path does not exist: {path}")

if __name__ == "__main__":
    test_transcriber()
