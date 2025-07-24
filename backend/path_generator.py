"""
Path Generator for Audiobook Organization
Generates standardized file paths based on Audible metadata
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use in filenames and paths
    Removes/replaces characters that are invalid in Windows/Unix filenames
    """
    if not text:
        return ""
    
    # Replace problematic characters with safe alternatives
    replacements = {
        ':': ' -',
        '?': '',
        '*': '',
        '"': "'",
        '<': '(',
        '>': ')',
        '|': '-',
        '/': '-',
        '\\': '-',
        '\n': ' ',
        '\r': ' ',
        '\t': ' '
    }
    
    sanitized = text
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)
    
    # Remove multiple spaces and trim
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Remove trailing dots and spaces (Windows doesn't like them)
    sanitized = sanitized.rstrip('. ')
    
    return sanitized


def extract_year(year_value) -> str:
    """
    Extract 4-digit year from various year formats
    """
    if not year_value:
        return ""
    
    year_str = str(year_value)
    year_match = re.search(r'(\d{4})', year_str)
    return year_match.group(1) if year_match else ""


def generate_audiobook_paths(audible_metadata: Dict, original_paths: List[str]) -> Dict:
    """
    Generate standardized file paths based on Audible metadata
    
    Format:
    Single Book: {Series Title}/{Book Number}-{Book Title} ({Release Year})/{Book Title}
    Multi-part Book: {Series Title}/{Book Number}-{Book Title} ({Release Year})/{Book Title} [Part XX]
    
    Args:
        audible_metadata: Selected Audible metadata from suggestions
        original_paths: List of original file paths
        
    Returns:
        Dict with 'organized_paths' and 'folder_structure' keys
    """
    
    # Extract metadata components
    series_title = audible_metadata.get('series', '') or audible_metadata.get('title', 'Unknown Series')
    book_title = audible_metadata.get('title', 'Unknown Title')
    book_number = audible_metadata.get('book_number')
    release_year = extract_year(audible_metadata.get('year'))
    
    # Sanitize components for filesystem
    series_clean = sanitize_filename(series_title)
    title_clean = sanitize_filename(book_title)
    
    # Build book number prefix
    book_num_prefix = f"{book_number}-" if book_number else ""
    
    # Build year suffix
    year_suffix = f" ({release_year})" if release_year else ""
    
    # Create folder structure
    folder_name = f"{book_num_prefix}{title_clean}{year_suffix}"
    series_folder = series_clean
    
    # Determine if this is single or multi-part
    num_files = len(original_paths)
    
    organized_paths = []
    
    if num_files == 1:
        # Single file audiobook
        original_ext = Path(original_paths[0]).suffix
        new_filename = f"{title_clean}{original_ext}"
        full_path = f"{series_folder}/{folder_name}/{new_filename}"
        organized_paths.append(full_path)
        
    else:
        # Multi-part audiobook - add [Part XX] to each file
        for i, original_path in enumerate(original_paths, 1):
            original_ext = Path(original_path).suffix
            part_num = f"{i:02d}"  # Zero-padded part number
            new_filename = f"{title_clean} [Part {part_num}]{original_ext}"
            full_path = f"{series_folder}/{folder_name}/{new_filename}"
            organized_paths.append(full_path)
    
    return {
        'organized_paths': organized_paths,
        'folder_structure': {
            'series_folder': series_folder,
            'book_folder': folder_name,
            'full_folder_path': f"{series_folder}/{folder_name}",
            'is_multi_part': num_files > 1,
            'part_count': num_files
        },
        'metadata_used': {
            'series': series_title,
            'title': book_title,
            'book_number': book_number,
            'year': release_year,
            'original_file_count': num_files
        }
    }


def generate_paths_for_audiobook(audiobook_data: Dict, selected_suggestion_index: int = 0) -> Optional[Dict]:
    """
    Generate organized paths for an audiobook based on selected Audible suggestion
    
    Args:
        audiobook_data: Full audiobook metadata (from JSON file)
        selected_suggestion_index: Index of selected Audible suggestion (default: 0)
        
    Returns:
        Path generation result or None if invalid data
    """
    
    # Get original paths
    original_metadata = audiobook_data.get('original', {})
    original_paths = original_metadata.get('paths', [])
    
    if not original_paths:
        print("[PATH_GEN] Warning: No original paths found")
        return None
    
    # Get selected Audible suggestion
    audible_suggestions = audiobook_data.get('audible_suggestions', [])
    
    if not audible_suggestions or selected_suggestion_index >= len(audible_suggestions):
        print(f"[PATH_GEN] Warning: Invalid suggestion index {selected_suggestion_index} or no suggestions")
        return None
    
    selected_audible = audible_suggestions[selected_suggestion_index]
    
    # Generate paths
    try:
        result = generate_audiobook_paths(selected_audible, original_paths)
        
        # Add original paths for reference
        result['original_paths'] = original_paths
        result['selected_suggestion'] = selected_audible
        result['suggestion_index'] = selected_suggestion_index
        
        print(f"[PATH_GEN] Generated {len(result['organized_paths'])} organized paths")
        return result
        
    except Exception as e:
        print(f"[PATH_GEN] Error generating paths: {e}")
        return None


def preview_organization(audiobook_data: Dict, selected_suggestion_index: int = 0) -> str:
    """
    Generate a preview string showing how files would be organized
    
    Args:
        audiobook_data: Full audiobook metadata
        selected_suggestion_index: Index of selected Audible suggestion
        
    Returns:
        Human-readable organization preview
    """
    
    result = generate_paths_for_audiobook(audiobook_data, selected_suggestion_index)
    
    if not result:
        return "Could not generate organization preview"
    
    preview_lines = []
    preview_lines.append(f"Organization Preview:")
    preview_lines.append(f"Series: {result['metadata_used']['series']}")
    preview_lines.append(f"Book: {result['metadata_used']['title']}")
    
    if result['metadata_used']['book_number']:
        preview_lines.append(f"Book Number: {result['metadata_used']['book_number']}")
    
    if result['metadata_used']['year']:
        preview_lines.append(f"Year: {result['metadata_used']['year']}")
    
    preview_lines.append(f"")
    preview_lines.append(f"Folder Structure:")
    preview_lines.append(f"└── {result['folder_structure']['full_folder_path']}/")
    
    for i, path in enumerate(result['organized_paths']):
        filename = Path(path).name
        prefix = "    ├── " if i < len(result['organized_paths']) - 1 else "    └── "
        preview_lines.append(f"{prefix}{filename}")
    
    return "\n".join(preview_lines)


# Test function for development
def test_path_generation():
    """Test the path generation with sample data"""
    
    # Sample audiobook data (similar to actual format)
    sample_data = {
        "original": {
            "paths": [
                "Robert Jordan - The Wheel of Time 12GB/(8) The Path of Daggers [64k 23;25;27 645MB]/[01] Into.mp3",
                "Robert Jordan - The Wheel of Time 12GB/(8) The Path of Daggers [64k 23;25;27 645MB]/[02] Chapter 1.mp3",
                "Robert Jordan - The Wheel of Time 12GB/(8) The Path of Daggers [64k 23;25;27 645MB]/[03] Chapter 2.mp3"
            ]
        },
        "audible_suggestions": [
            {
                "title": "Path of Daggers",
                "subtitle": "Book Eight of The Wheel of Time",
                "author": "Robert Jordan",
                "series": "The Wheel of Time",
                "book_number": 8,
                "year": "2008"
            }
        ]
    }
    
    result = generate_paths_for_audiobook(sample_data, 0)
    print("Test Result:")
    print(result)
    
    preview = preview_organization(sample_data, 0)
    print("\nPreview:")
    print(preview)


if __name__ == "__main__":
    test_path_generation()
