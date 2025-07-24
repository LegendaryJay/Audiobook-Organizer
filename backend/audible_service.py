"""
Audible Search Service for Audiobook Metadata Enhancement
Automatically searches Audible when new audiobooks are detected
"""

import json
import os
import re
import subprocess
import requests
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import difflib

try:
    from audiobook_transcriber import get_transcription_metadata
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TRANSCRIPTION_AVAILABLE = False

# Path generation imports
generate_paths_for_audiobook = None
preview_organization = None
PATH_GENERATION_AVAILABLE = False

try:
    from path_generator import generate_paths_for_audiobook, preview_organization
    PATH_GENERATION_AVAILABLE = True
except ImportError:
    pass

class AudibleSearchService:
    """Service for searching and enriching audiobook metadata from Audible"""
    
    def __init__(self, covers_dir: Path):
        self.covers_dir = Path(covers_dir)
        self.covers_dir.mkdir(exist_ok=True)
        print("[AUDIBLE] Service initialized - using direct Audible series data")
    
    def search_audible(self, query_data: Dict) -> Optional[List[Dict]]:
        """
        Search Audible using the audible-cli
        Args:
            query_data: Dict with keys: asin, title, author, filename
        Returns:
            List of product metadata or None if no results
        """
        asin = query_data.get('asin')
        title = query_data.get('title')
        author = query_data.get('author')
        filename = query_data.get('filename')
        
        def clean_query(s):
            """Clean query string for better search results"""
            if not s:
                return ""
            # Remove special characters, keep letters and spaces
            return re.sub(r'[^a-zA-Z ]+', ' ', str(s)).strip()
        
        def run_audible_query(query_string):
            """Execute audible CLI search"""
            print(f'[AUDIBLE SEARCH] {query_string}')
            try:
                cli_cmd = [
                    'audible', 'api', '/1.0/catalog/products',
                    '-p', f'keywords={query_string}',
                    '-p', 'num_results=10',
                    '-p', 'response_groups=product_desc,product_attrs,media,series',
                    '-f', 'json'
                ]
                
                result = subprocess.run(cli_cmd, capture_output=True, text=True, check=True)
                data = json.loads(result.stdout)
                products = data.get('products', {})
                
                product_list = []
                if isinstance(products, dict):
                    for asin_key, meta in products.items():
                        meta['asin'] = asin_key
                        product_list.append(meta)
                elif isinstance(products, list):
                    for meta in products:
                        meta['asin'] = meta.get('asin', '')
                        product_list.append(meta)
                
                return product_list if product_list else None
                
            except subprocess.CalledProcessError as e:
                print(f'[ERROR] Audible CLI failed: {e}')
                return None
            except Exception as e:
                print(f'[ERROR] Audible search error: {e}')
                return None
        
        # Search strategy: 1. ASIN (exact), 2. Title + Author, 3. Title only, 4. Filename
        search_queries = []
        
        # 1. ASIN search (highest priority)
        if asin:
            search_queries.append(('asin', asin))
        
        # 2. Title + Author search
        if title and author:
            query = f"{clean_query(title)} {clean_query(author)}"
            if query.strip():
                search_queries.append(('title_author', query))
        
        # 3. Title only search
        if title:
            query = clean_query(title)
            if query.strip():
                search_queries.append(('title', query))
        
        # 4. Filename search (fallback) - Enhanced to use folder names
        if filename:
            # Use the parent folder name instead of individual file name for better results
            path_obj = Path(filename)
            folder_name = path_obj.parent.name if path_obj.parent.name != '.' else path_obj.stem
            query = clean_query(folder_name)
            if query.strip():
                search_queries.append(('folder_name', query))
        
        # Execute searches in priority order
        for search_type, query in search_queries:
            results = run_audible_query(query)
            if results:
                print(f'[AUDIBLE] Found {len(results)} results using {search_type} search')
                return results
        
        print('[AUDIBLE] No results found with any search strategy')
        return None
    
    def calculate_match_score(self, audible_meta: Dict, local_meta: Dict) -> float:
        """
        Calculate match score between Audible metadata and local file
        Returns score 0.0-1.0 (1.0 = perfect match)
        """
        score = 0.0
        total_weight = 0.0
        
        # ASIN match (highest weight)
        if local_meta.get('asin') and audible_meta.get('asin'):
            total_weight += 0.4
            if local_meta['asin'].lower() == audible_meta['asin'].lower():
                score += 0.4
        
        # Title similarity (high weight)
        local_title = str(local_meta.get('title', '')).lower()
        audible_title = str(audible_meta.get('title', '')).lower()
        if local_title and audible_title:
            total_weight += 0.3
            title_similarity = difflib.SequenceMatcher(None, local_title, audible_title).ratio()
            score += 0.3 * title_similarity
        
        # Author similarity (medium weight)
        local_author = str(local_meta.get('author', '')).lower()
        audible_author = str(audible_meta.get('authors', [{}])[0].get('name', '') or 
                           audible_meta.get('author', '')).lower()
        if local_author and audible_author:
            total_weight += 0.2
            author_similarity = difflib.SequenceMatcher(None, local_author, audible_author).ratio()
            score += 0.2 * author_similarity
        
        # Runtime length similarity (higher weight for better selection)
        local_runtime = local_meta.get('runtime_length_min')
        audible_runtime = audible_meta.get('runtime_length_min')
        if local_runtime and audible_runtime:
            total_weight += 0.25  # Increased from 0.1 to 0.25
            # Calculate percentage difference
            diff_percent = abs(local_runtime - audible_runtime) / max(local_runtime, audible_runtime)
            runtime_score = max(0, 1 - diff_percent)  # Perfect match = 1, big difference = 0
            score += 0.25 * runtime_score
        
        # Return normalized score
        return score / total_weight if total_weight > 0 else 0.0
    
    def rank_search_results(self, results: List[Dict], local_meta: Dict) -> List[Tuple[Dict, float]]:
        """
        Rank search results by match quality
        Returns list of (metadata, score) tuples sorted by best match first
        """
        scored_results = []
        for result in results:
            score = self.calculate_match_score(result, local_meta)
            scored_results.append((result, score))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results
    
    def extract_audible_metadata_basic(self, audible_meta: Dict, uuid_str: str) -> Dict:
        """
        Extract basic metadata from Audible response (without series enhancement)
        Args:
            audible_meta: Raw Audible API response
            uuid_str: UUID for audiobook file (used as fallback identifier)
        Returns:
            Basic metadata dict without book number lookup
        """
        # Get best available cover image URL (largest size)
        cover_url = None
        product_images = audible_meta.get('product_images', {})
        for size in ['2560', '1024', '500', '256', '128']:
            if size in product_images:
                cover_url = product_images[size]
                break
        
        # Use cover URL directly instead of downloading
        cover_path = cover_url if cover_url else None
        
        # Extract authors
        authors = audible_meta.get('authors', [])
        author = authors[0].get('name') if authors else audible_meta.get('author', '')
        
        # Extract narrators
        narrators = audible_meta.get('narrators', [])
        narrator = ', '.join([n.get('name', '') for n in narrators]) if narrators else ''
        
        # Extract publication year from release_date
        release_date = audible_meta.get('release_date', '')
        year_match = re.search(r'(\d{4})', str(release_date))
        year = year_match.group(1) if year_match else ''
        
        # Extract series information including book number from Audible data
        series_info = audible_meta.get('series', [])
        series_name = series_info[0].get('title') if series_info else ''
        
        # Extract book number directly from Audible series sequence
        book_number = None
        if series_info:
            sequence = series_info[0].get('sequence')
            if sequence:
                try:
                    book_number = int(sequence)
                    print(f"[AUDIBLE] Found book number from Audible series data: {book_number}")
                except (ValueError, TypeError):
                    print(f"[AUDIBLE] Could not parse sequence as integer: {sequence}")
        
        # Extract genres/categories
        categories = audible_meta.get('categories', [])
        genres = [cat.get('name', '') for cat in categories if cat.get('name')]
        
        return {
            'title': audible_meta.get('title', ''),
            'subtitle': audible_meta.get('subtitle', ''),
            'author': author,
            'narrator': narrator,
            'series': series_name,
            'book_number': book_number,  # Now extracted directly from Audible
            'year': year,
            'genre': genres,
            'asin': audible_meta.get('asin', ''),
            'audible_url': f"https://www.audible.com/pd/{audible_meta.get('asin', '')}",
            'runtime_length_min': audible_meta.get('runtime_length_min'),
            'coverImage': cover_path,
            'cover_url': cover_path,  # Direct URL to Audible cover
            'publisher': audible_meta.get('publisher_name', ''),
            'language': audible_meta.get('language', ''),
            'description': audible_meta.get('publisher_summary', ''),
            'rating': audible_meta.get('overall_rating', {}).get('display_average_rating'),
            'num_ratings': audible_meta.get('overall_rating', {}).get('num_ratings')
        }

    def enhance_with_book_number(self, audible_meta: Dict, basic_metadata: Dict) -> Dict:
        """
        No longer needed since book numbers are extracted directly from Audible
        This method now just returns the basic metadata unchanged
        """
        return basic_metadata

    def extract_audible_metadata(self, audible_meta: Dict, uuid_str: str) -> Dict:
        """
        Extract relevant metadata from Audible response
        Args:
            audible_meta: Raw Audible API response
            uuid_str: UUID for audiobook file (used as fallback identifier)
        Returns:
            Standardized metadata dict
        """
        # Get best available cover image URL (largest size)
        cover_url = None
        product_images = audible_meta.get('product_images', {})
        for size in ['2560', '1024', '500', '256', '128']:
            if size in product_images:
                cover_url = product_images[size]
                break
        
        # Use cover URL directly instead of downloading
        cover_path = cover_url if cover_url else None
        
        # Extract authors
        authors = audible_meta.get('authors', [])
        author = authors[0].get('name') if authors else audible_meta.get('author', '')
        
        # Extract narrators
        narrators = audible_meta.get('narrators', [])
        narrator = ', '.join([n.get('name', '') for n in narrators]) if narrators else ''
        
        # Extract publication year from release_date
        release_date = audible_meta.get('release_date', '')
        year_match = re.search(r'(\d{4})', str(release_date))
        year = year_match.group(1) if year_match else ''
        
        # Extract series information directly from Audible
        series_info = audible_meta.get('series', [])
        series_name = series_info[0].get('title') if series_info else ''
        
        # Extract book number directly from Audible series sequence
        book_number = None
        if series_info:
            sequence = series_info[0].get('sequence')
            if sequence:
                try:
                    book_number = int(sequence)
                    print(f"[AUDIBLE] Found book number from Audible series data: {book_number}")
                except (ValueError, TypeError):
                    print(f"[AUDIBLE] Could not parse sequence as integer: {sequence}")
        
        # Extract publication year from release_date
        release_date = audible_meta.get('release_date', '')
        year_match = re.search(r'(\d{4})', str(release_date))
        year = year_match.group(1) if year_match else ''
        
        # Extract genres/categories
        categories = audible_meta.get('categories', [])
        genres = [cat.get('name', '') for cat in categories if cat.get('name')]
        
        return {
            'title': audible_meta.get('title', ''),
            'subtitle': audible_meta.get('subtitle', ''),
            'author': author,
            'narrator': narrator,
            'series': series_name,
            'book_number': book_number,
            'year': year,
            'genre': genres,
            'asin': audible_meta.get('asin', ''),
            'audible_url': f"https://www.audible.com/pd/{audible_meta.get('asin', '')}",
            'runtime_length_min': audible_meta.get('runtime_length_min'),
            'coverImage': cover_path,
            'cover_url': cover_path,  # Direct URL to Audible cover
            'publisher': audible_meta.get('publisher_name', ''),
            'language': audible_meta.get('language', ''),
            'description': audible_meta.get('publisher_summary', ''),
            'rating': audible_meta.get('overall_rating', {}).get('display_average_rating'),
            'num_ratings': audible_meta.get('overall_rating', {}).get('num_ratings')
        }
    
    def generate_organized_paths(self, audiobook_data: Dict, selected_suggestion_index: int = 0) -> Optional[Dict]:
        """
        Generate organized file paths for an audiobook based on selected Audible suggestion
        
        Args:
            audiobook_data: Full audiobook metadata (from JSON file)
            selected_suggestion_index: Index of selected Audible suggestion
            
        Returns:
            Path generation result or None if path generation not available
        """
        if not PATH_GENERATION_AVAILABLE or generate_paths_for_audiobook is None:
            print("[AUDIBLE] Warning: Path generation not available - path_generator module not found")
            return None
        
        try:
            return generate_paths_for_audiobook(audiobook_data, selected_suggestion_index)
        except Exception as e:
            print(f"[AUDIBLE] Error generating organized paths: {e}")
            return None
    
    def preview_audiobook_organization(self, audiobook_data: Dict, selected_suggestion_index: int = 0) -> str:
        """
        Generate a preview of how files would be organized
        
        Args:
            audiobook_data: Full audiobook metadata
            selected_suggestion_index: Index of selected Audible suggestion
            
        Returns:
            Human-readable organization preview
        """
        if not PATH_GENERATION_AVAILABLE or preview_organization is None:
            return "Path generation not available - missing path_generator module"
        
        try:
            return preview_organization(audiobook_data, selected_suggestion_index)
        except Exception as e:
            return f"Error generating preview: {e}"
    
    def enhance_audiobook_metadata(self, local_metadata: Dict, audiobook_uuid: str) -> Dict:
        """
        Main method to enhance audiobook metadata with Audible data
        Returns dict with original metadata and ranked Audible suggestions
        """
        print(f'[AUDIBLE] Enhancing metadata for: {local_metadata.get("title", "Unknown")}')
        
        # Search Audible
        search_query = {
            'asin': local_metadata.get('asin', ''),
            'title': local_metadata.get('title', ''),
            'author': local_metadata.get('author', ''),
            'filename': local_metadata.get('paths', [''])[0] if local_metadata.get('paths') else ''
        }
        
        search_results = self.search_audible(search_query)
        
        if not search_results:
            print('[AUDIBLE] No search results found')
            return {
                'audible_enhanced': False,
                'audible_suggestions': [],
                'message': 'No Audible results found'
            }
        
        # Rank results by match quality
        ranked_results = self.rank_search_results(search_results, local_metadata)
        
        # Extract metadata for all matches (without book numbers for speed)
        suggestions = []
        for i, (audible_meta, score) in enumerate(ranked_results[:10]):  # Top 10 matches
            enhanced_meta = self.extract_audible_metadata_basic(audible_meta, audiobook_uuid)
            enhanced_meta['id'] = i + 1  # Add sequential ID starting from 1
            enhanced_meta['match_score'] = score
            enhanced_meta['match_confidence'] = 'high' if score > 0.8 else 'medium' if score > 0.5 else 'low'
            
            # Generate organized paths for this suggestion
            if PATH_GENERATION_AVAILABLE and generate_paths_for_audiobook is not None:
                try:
                    # Create a temporary audiobook data structure for path generation
                    temp_audiobook_data = {
                        'original': local_metadata,
                        'audible_suggestions': [enhanced_meta]
                    }
                    path_result = generate_paths_for_audiobook(temp_audiobook_data, 0)
                    if path_result and path_result.get('organized_paths'):
                        # Use organized paths as the main paths field
                        enhanced_meta['paths'] = path_result['organized_paths']
                    else:
                        # Fallback to original paths if path generation fails
                        enhanced_meta['paths'] = local_metadata.get('paths', [])
                except Exception as e:
                    print(f"[AUDIBLE] Warning: Could not generate paths for suggestion: {e}")
                    # Fallback to original paths if path generation fails
                    enhanced_meta['paths'] = local_metadata.get('paths', [])
            else:
                # Use original paths if path generation not available
                enhanced_meta['paths'] = local_metadata.get('paths', [])
            
            suggestions.append(enhanced_meta)
        
        # Enhance ONLY the best match with book number information
        if suggestions:
            best_match = suggestions[0]
            print(f"[AUDIBLE] Enhancing best match with series info: {best_match['title']}")
            enhanced_best = self.enhance_with_book_number(ranked_results[0][0], best_match)
            suggestions[0] = enhanced_best
        
        best_match = suggestions[0] if suggestions else None
        selected_id = 1 if suggestions else None  # Default to first suggestion (ID 1)
        
        return {
            'audible_enhanced': True,
            'audible_suggestions': suggestions,
            'best_match': best_match,
            'selected_audible_id': selected_id,  # Track which suggestion is selected
            'total_results': len(search_results),
            'message': f'Found {len(suggestions)} ranked suggestions'
        }


def test_audible_service():
    """Test function for the Audible service"""
    service = AudibleSearchService(Path('./covers'))
    
    test_metadata = {
        'title': 'The Way of Kings',
        'author': 'Brandon Sanderson',
        'runtime_length_min': 2850,
        'paths': ['The Way of Kings.m4b']
    }
    
    result = service.enhance_audiobook_metadata(test_metadata, str(uuid.uuid4()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    test_audible_service()
