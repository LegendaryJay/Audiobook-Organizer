"""
Book Series Service
Uses external APIs to find book series information including book numbers
"""

import requests
import re
from typing import Dict, List, Optional, Tuple
import json
import time
from urllib.parse import quote_plus

class BookSeriesService:
    """Service to find book series information using external APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AudiobookOrganizer/1.0 (Book Series Lookup)'
        })
        
    def search_open_library(self, title: str, author: str) -> Optional[Dict]:
        """
        Search Open Library for book series information
        Returns book position, series name, and total books if available
        """
        try:
            # Clean up title and author for search
            clean_title = self._clean_search_term(title)
            clean_author = self._clean_search_term(author)
            
            # Build search query
            query = f'title:"{clean_title}"'
            if clean_author:
                query += f' author:"{clean_author}"'
            
            url = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit=10"
            
            print(f"[SERIES] Searching Open Library: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('docs'):
                return None
            
            # Look for the best match
            for doc in data['docs']:
                series_info = self._extract_series_from_openlibrary(doc)
                if series_info:
                    return series_info
            
            return None
            
        except Exception as e:
            print(f"[SERIES] Open Library search failed: {e}")
            return None
    
    def search_google_books(self, title: str, author: str) -> Optional[Dict]:
        """
        Search Google Books API for series information
        """
        try:
            # Clean up search terms
            clean_title = self._clean_search_term(title)
            clean_author = self._clean_search_term(author)
            
            # Build search query
            query = f'intitle:"{clean_title}"'
            if clean_author:
                query += f' inauthor:"{clean_author}"'
            
            url = f"https://www.googleapis.com/books/v1/volumes?q={quote_plus(query)}&maxResults=10"
            
            print(f"[SERIES] Searching Google Books: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                return None
            
            # Look for series information in results
            for item in data['items']:
                series_info = self._extract_series_from_google_books(item)
                if series_info:
                    return series_info
            
            return None
            
        except Exception as e:
            print(f"[SERIES] Google Books search failed: {e}")
            return None
    
    def find_book_series_info(self, title: str, author: str) -> Dict:
        """
        Main method to find book series information
        Tries multiple APIs and returns the best result
        """
        print(f"[SERIES] Finding series info for: {title} by {author}")
        
        result = {
            'series_name': '',
            'book_number': None,
            'total_books': None,
            'series_position': '',  # e.g., "Book 3 of 14"
            'source': '',
            'found': False
        }
        
        # Try Open Library first (free and good)
        ol_result = self.search_open_library(title, author)
        if ol_result:
            result.update(ol_result)
            result['source'] = 'Open Library'
            result['found'] = True
            return result
        
        # Try Google Books as fallback
        gb_result = self.search_google_books(title, author)
        if gb_result:
            result.update(gb_result)
            result['source'] = 'Google Books'
            result['found'] = True
            return result
        
        # If no API results, try to extract from title
        title_result = self._extract_series_from_title(title)
        if title_result:
            result.update(title_result)
            result['source'] = 'Title Parsing'
            result['found'] = True
        
        return result
    
    def _extract_series_from_openlibrary(self, doc: Dict) -> Optional[Dict]:
        """Extract series information from Open Library document"""
        try:
            # Look for series in the document
            series_data = {}
            
            # Check if there's series information
            if 'series' in doc and doc['series']:
                series_name = doc['series'][0] if isinstance(doc['series'], list) else doc['series']
                series_data['series_name'] = series_name
            
            # Look for book number in title or subject
            title = doc.get('title', '')
            
            # Try to extract book number from title
            book_num = self._extract_book_number_from_text(title)
            if book_num:
                series_data['book_number'] = book_num
            
            # Look in subjects for series info
            subjects = doc.get('subject', [])
            for subject in subjects:
                if isinstance(subject, str):
                    series_match = self._extract_series_from_subject(subject)
                    if series_match:
                        series_data.update(series_match)
            
            if series_data:
                return series_data
            
            return None
            
        except Exception as e:
            print(f"[SERIES] Error extracting from Open Library doc: {e}")
            return None
    
    def _extract_series_from_google_books(self, item: Dict) -> Optional[Dict]:
        """Extract series information from Google Books item"""
        try:
            volume_info = item.get('volumeInfo', {})
            series_data = {}
            
            # Check title for series info
            title = volume_info.get('title', '')
            subtitle = volume_info.get('subtitle', '')
            full_title = f"{title} {subtitle}".strip()
            
            # Look for book number in title
            book_num = self._extract_book_number_from_text(full_title)
            if book_num:
                series_data['book_number'] = book_num
            
            # Look for series name in categories or description
            categories = volume_info.get('categories', [])
            description = volume_info.get('description', '')
            
            # Try to extract series from description
            series_match = self._extract_series_from_description(description)
            if series_match:
                series_data.update(series_match)
            
            if series_data:
                return series_data
            
            return None
            
        except Exception as e:
            print(f"[SERIES] Error extracting from Google Books item: {e}")
            return None
    
    def _extract_book_number_from_text(self, text: str) -> Optional[int]:
        """Extract book number from text using various patterns"""
        if not text:
            return None
        
        patterns = [
            r'book\s+(\d+)',                    # "Book 12"
            r'#(\d+)',                          # "#12"
            r'\((\d+)\)',                       # "(12)"
            r'volume\s+(\d+)',                  # "Volume 12"
            r'part\s+(\d+)',                    # "Part 12"
            r'number\s+(\d+)',                  # "Number 12"
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_series_from_subject(self, subject: str) -> Optional[Dict]:
        """Extract series info from Open Library subject"""
        # Look for patterns like "Wheel of Time (Series)"
        series_patterns = [
            r'(.+?)\s*\(series\)',
            r'(.+?)\s*series',
            r'(.+?)\s*\(book series\)',
        ]
        
        for pattern in series_patterns:
            match = re.search(pattern, subject.lower())
            if match:
                series_name = match.group(1).strip().title()
                return {'series_name': series_name}
        
        return None
    
    def _extract_series_from_description(self, description: str) -> Optional[Dict]:
        """Extract series info from book description"""
        if not description:
            return None
        
        # Look for patterns in description
        patterns = [
            r'book\s+(\d+)\s+(?:of|in)\s+(?:the\s+)?(.+?)\s+series',
            r'(\d+)(?:st|nd|rd|th)\s+book\s+in\s+(?:the\s+)?(.+?)\s+series',
            r'part\s+(\d+)\s+of\s+(?:the\s+)?(.+?)\s+(?:series|saga)',
            r'(?:the\s+)?(.+?)\s+(?:series|saga)',  # Just find series name
            r'(.+?)\s+is\s+(?:a|an)\s+(?:original\s+)?series',  # "Wheel of Time is now an original series"
        ]
        
        description_lower = description.lower()
        
        # First try patterns with book numbers
        for pattern in patterns[:-2]:
            match = re.search(pattern, description_lower)
            if match:
                try:
                    book_num = int(match.group(1))
                    series_name = match.group(2).strip().title()
                    return {
                        'book_number': book_num,
                        'series_name': series_name
                    }
                except (ValueError, IndexError):
                    continue
        
        # Then try to just find series names
        series_patterns = [
            r'(?:the\s+)?([A-Z][a-zA-Z\s]+?)\s+(?:is\s+now\s+an?\s+.*?\s+series|series)',
            r'(?:the\s+)?([A-Z][a-zA-Z\s]+?)\s+by\s+[A-Z][a-zA-Z\s]+\s+has\s+captivated',
            r'since\s+its\s+debut.*?(?:the\s+)?([A-Z][a-zA-Z\s]+?)®?\s+by',
        ]
        
        for pattern in series_patterns:
            match = re.search(pattern, description)
            if match:
                series_name = match.group(1).strip()
                # Clean up series name
                series_name = re.sub(r'®', '', series_name)
                if len(series_name) > 3 and len(series_name) < 50:  # Reasonable length
                    return {'series_name': series_name}
        
        return None
    
    def _extract_series_from_title(self, title: str) -> Optional[Dict]:
        """Fallback: Extract series info directly from title"""
        if not title:
            return None
        
        # Look for common title patterns
        patterns = [
            r'(.+?)\s*\((.+?)\s*#(\d+)\)',           # "Title (Series #3)"
            r'(.+?)\s*\((.+?)\s*book\s*(\d+)\)',     # "Title (Series Book 3)"
            r'(.+?)\s*:\s*(.+?)\s*#(\d+)',           # "Title: Series #3"
            r'(.+?)\s*-\s*(.+?)\s*#(\d+)',           # "Title - Series #3"
            r'(.+?)\s*book\s*(\d+)',                 # "Series Title Book 3"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:
                        title_part, series_name, book_num = match.groups()
                        return {
                            'series_name': series_name.strip(),
                            'book_number': int(book_num)
                        }
                    elif len(match.groups()) == 2:
                        series_name, book_num = match.groups()
                        return {
                            'series_name': series_name.strip(),
                            'book_number': int(book_num)
                        }
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _clean_search_term(self, term: str) -> str:
        """Clean search term for API queries"""
        if not term:
            return ''
        
        # Remove common patterns that might interfere with search
        term = re.sub(r'\s*\(.*?\)\s*', ' ', term)  # Remove parentheses
        term = re.sub(r'\s*#\d+\s*', ' ', term)     # Remove #numbers
        term = re.sub(r'\s*book\s*\d+\s*', ' ', term, flags=re.IGNORECASE)  # Remove "book X"
        term = re.sub(r'\s+', ' ', term)            # Normalize spaces
        
        return term.strip()


# Example usage and testing
if __name__ == "__main__":
    service = BookSeriesService()
    
    # Test with some examples
    test_books = [
        ("The Gathering Storm", "Robert Jordan"),
        ("Ignite Me", "Tahereh Mafi"),
        ("The Eye of the World", "Robert Jordan"),
    ]
    
    for title, author in test_books:
        print(f"\n--- Testing: {title} by {author} ---")
        result = service.find_book_series_info(title, author)
        print(json.dumps(result, indent=2))
