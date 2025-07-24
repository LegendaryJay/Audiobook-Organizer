"""
Enhanced Audiobook Transcriber
Extracts and transcribes audio to identify metadata from spoken introductions
"""

import subprocess
import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from mutagen._file import File

class AudiobookTranscriber:
    """Enhanced audiobook transcriber with metadata extraction capabilities"""
    
    def __init__(self, default_duration=90):
        self.default_duration = default_duration  # 90 seconds default
        self.temp_files = []
        self.dependencies_checked = False
        self.pydub_available = False
        self.sr_available = False
        self.whisper_available = False
    
    def check_dependencies(self):
        """Check and report available transcription methods"""
        if self.dependencies_checked:
            return
        
        # Check pydub for audio processing
        try:
            import pydub
            self.pydub_available = True
            print("[TRANSCRIBER] pydub available for audio processing")
        except ImportError:
            print("[TRANSCRIBER] pydub not available. Install with: pip install pydub")
        
        # Check SpeechRecognition
        try:
            import speech_recognition
            self.sr_available = True
            print("[TRANSCRIBER] SpeechRecognition available")
        except ImportError:
            print("[TRANSCRIBER] SpeechRecognition not available. Install with: pip install SpeechRecognition")
        
        # Check whisper for local transcription
        try:
            import whisper
            self.whisper_available = True
            print("[TRANSCRIBER] Whisper available for local transcription")
        except ImportError:
            print("[TRANSCRIBER] Whisper not available. Install with: pip install openai-whisper")
        
        # Check ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            print("[TRANSCRIBER] ffmpeg available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[TRANSCRIBER] ffmpeg not available. Required for audio processing.")
        
        self.dependencies_checked = True
    
    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"[TRANSCRIBER] Warning: Could not remove temp file {temp_file}: {e}")
        self.temp_files = []
    
    def detect_audiobook_structure(self, folder_path: str) -> Dict:
        """
        Analyze folder structure to determine if it's multi-file or single-file audiobook
        """
        folder = Path(folder_path)
        audio_extensions = {'.mp3', '.m4a', '.m4b', '.flac', '.wav', '.ogg', '.aac'}
        
        audio_files = []
        for file_path in folder.rglob('*'):
            if file_path.suffix.lower() in audio_extensions:
                audio_files.append(file_path)
        
        if not audio_files:
            return {'type': 'no_audio', 'files': []}
        
        if len(audio_files) == 1:
            # Check if single file has chapters
            has_chapters = self.has_chapters(audio_files[0])
            return {
                'type': 'single_file_with_chapters' if has_chapters else 'single_file_no_chapters',
                'files': audio_files,
                'primary_file': audio_files[0]
            }
        else:
            # Multiple files - sort by name to get first file
            audio_files.sort(key=lambda x: x.name.lower())
            return {
                'type': 'multi_file',
                'files': audio_files,
                'first_file': audio_files[0]
            }
    
    def has_chapters(self, audio_file: Path) -> bool:
        """Check if audio file has chapter information"""
        try:
            # Try ffprobe first
            result = subprocess.run([
                "ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", str(audio_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                chapters = info.get("chapters", [])
                return len(chapters) > 0
        except Exception:
            pass
        
        # Try mutagen for MP4 files
        try:
            audio = File(str(audio_file))
            if audio and hasattr(audio, 'chapters') and audio.chapters:
                return len(audio.chapters) > 0
        except Exception:
            pass
        
        return False
    
    def get_chapters_ffprobe(self, audio_file: Path) -> List[Dict]:
        """Extract chapter information using ffprobe"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", str(audio_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                chapters = info.get("chapters", [])
                chapter_list = []
                
                for ch in chapters:
                    start = float(ch.get("start_time", 0))
                    end = float(ch.get("end_time", 0))
                    title = ch.get("tags", {}).get("title", f"Chapter {len(chapter_list) + 1}")
                    chapter_list.append({
                        "start": start,
                        "end": end,
                        "title": title,
                        "duration": end - start
                    })
                
                return chapter_list
        except Exception as e:
            print(f"[TRANSCRIBER] Error getting chapters: {e}")
        
        return []
    
    def extract_audio_segment(self, input_file: Path, start_time: float = 0, duration: Optional[float] = None) -> Optional[str]:
        """
        Extract audio segment using ffmpeg (works without pydub)
        Returns path to temporary WAV file
        """
        if duration is None:
            duration = self.default_duration
        
        output_file = f"temp_segment_{hash(str(input_file))}_{start_time:.0f}s.wav"
        output_path = Path(output_file).absolute()
        
        try:
            # Use ffmpeg to extract segment
            cmd = [
                "ffmpeg", "-i", str(input_file),
                "-ss", str(start_time),
                "-t", str(duration),
                "-acodec", "pcm_s16le",
                "-ar", "16000",  # 16kHz for speech recognition
                "-ac", "1",      # Mono
                "-y",            # Overwrite output file
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_path.exists():
                self.temp_files.append(str(output_path))
                return str(output_path)
            else:
                print(f"[TRANSCRIBER] ffmpeg error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"[TRANSCRIBER] Error extracting audio segment: {e}")
            return None
    
    def transcribe_with_whisper(self, audio_file: str) -> Optional[str]:
        """Transcribe audio using local Whisper model"""
        try:
            import whisper
            
            # Load small model for speed (can use 'base' or 'small')
            model = whisper.load_model("tiny")  # Fastest model
            
            # Transcribe
            result = model.transcribe(audio_file)
            # If result["text"] is a list, join it; otherwise, use as is
            text = result["text"]
            if isinstance(text, list):
                text = " ".join(text)
            text = text.strip()
            
            print(f"[TRANSCRIBER] Whisper transcription: {text[:100]}...")
            return text
            
        except Exception as e:
            print(f"[TRANSCRIBER] Whisper transcription failed: {e}")
            return None
    
    def transcribe_with_speech_recognition(self, audio_file: str) -> Optional[str]:
        """Transcribe audio using SpeechRecognition (requires internet)"""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
            
            # Try Google Speech Recognition
            text = recognizer.recognize_google(audio_data)
            print(f"[TRANSCRIBER] Google SR transcription: {text[:100]}...")
            return text
            
        except Exception as e:
            print(f"[TRANSCRIBER] Speech Recognition failed: {e}")
            return None
    
    def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio using available methods (prefer local Whisper)
        """
        self.check_dependencies()
        
        # Try Whisper first (local, more accurate)
        if self.whisper_available:
            result = self.transcribe_with_whisper(audio_file)
            if result:
                return result
        
        # Fallback to SpeechRecognition
        if self.sr_available:
            result = self.transcribe_with_speech_recognition(audio_file)
            if result:
                return result
        
        print("[TRANSCRIBER] No transcription methods available")
        return None
    
    def clean_title_text(self, text: str) -> str:
        """Clean title text by removing common words and converting numbers"""
        if not text:
            return text
        
        # Convert number words to digits
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'eleven': '11', 'twelve': '12', 'thirteen': '13', 'fourteen': '14', 
            'fifteen': '15', 'sixteen': '16', 'seventeen': '17', 'eighteen': '18', 
            'nineteen': '19', 'twenty': '20'
        }
        
        # Replace number words (case insensitive)
        for word, digit in number_words.items():
            text = re.sub(rf'\b{word}\b', digit, text, flags=re.IGNORECASE)
        
        # Remove common series-related words
        words_to_remove = ['series', 'book', 'trilogy', 'novel', 'part']
        for word in words_to_remove:
            text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def extract_metadata_from_transcription(self, text: str) -> Dict:
        """
        Extract audiobook metadata from transcription text
        Looking for patterns like:
        - "Company presents"
        - "Book Title with Subtitle"
        - "Written by Author"
        - "Narrated by Narrator"
        """
        metadata = {
            'title': None,
            'subtitle': None,
            'author': None,
            'narrator': None,
            'publisher': None,
            'platform': None,
            'raw_transcription': text
        }
        
        text_lower = text.lower()
        
        # Remove "this is audible" from the beginning if present
        text_lower = re.sub(r'^.*?this is audible\.?\s*', '', text_lower)
        
        # Detect platform (but don't include it in publisher extraction)
        if 'audible' in text_lower:
            metadata['platform'] = 'Audible'
        elif 'libro.fm' in text_lower:
            metadata['platform'] = 'Libro.fm'
        
        # Extract publisher/company (before "presents", excluding "audible")
        publisher_match = re.search(r'(.*?)\s+presents\s+', text_lower)
        if publisher_match:
            publisher_text = publisher_match.group(1).strip()
            # Remove "this is audible" but keep "audible" when it's part of company name
            publisher_text = re.sub(r'^.*?this is audible\.?\s*', '', publisher_text)
            publisher_text = publisher_text.strip()
            if publisher_text:
                metadata['publisher'] = publisher_text
        
        # Extract author (after "written by" or "by")
        author_patterns = [
            r'written by\s+([^,]+?)(?:\s+performed|\s+narrated|\s+read|\s+chapter)',
            r'by\s+([a-zA-Z\.\s]+?)(?:\s+performed|\s+narrated|\s+read)',
            r'author[:\s]+([^,\.]+)'
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, text_lower)
            if match:
                author_text = match.group(1).strip()
                # Clean up common artifacts but preserve periods in names
                author_text = re.sub(r'\s+performed.*$', '', author_text)
                author_text = re.sub(r'\s+read.*$', '', author_text)
                author_text = re.sub(r'\s+narrated.*$', '', author_text)
                if author_text and len(author_text) > 1:  # Only set if we have something meaningful
                    metadata['author'] = author_text.title()
                    break
        
        # Extract narrator (after "narrated by", "read by", or "performed by")
        narrator_patterns = [
            r'performed by\s+([^,\.]+)',
            r'narrated by\s+([^,\.]+)',
            r'read by\s+([^,\.]+)',
            r'read for you by\s+([^,\.]+)',
            r'narrator[:\s]+([^,\.]+)'
        ]
        
        for pattern in narrator_patterns:
            match = re.search(pattern, text_lower)
            if match:
                narrator_text = match.group(1).strip()
                # Clean up common artifacts
                narrator_text = re.sub(r'\s+chapter.*$', '', narrator_text)
                narrator_text = re.sub(r'\s+and.*$', '', narrator_text)  # Handle "read by John and Jane"
                metadata['narrator'] = narrator_text.title()
                break
        
        # Extract title (this is trickier - between company/presents and written by)
        # Look for text between "presents" and "written by"/"by"
        title_patterns = [
            r'presents\s+([^\.]+?)(?:\s+written by|\s+by|\s+author)',
            r'audio presents\s+([^\.]+?)(?:\s+written by|\s+by|\s+author)',
            r'presents\s+([^,]+?)(?:\s+performed by|\s+narrated by|\s+read by)'
        ]
        
        for pattern in title_patterns:
            title_match = re.search(pattern, text_lower)
            if title_match:
                potential_title = title_match.group(1).strip()
                
                # Clean the title text
                potential_title = self.clean_title_text(potential_title)
                
                # Check for subtitle (separated by colon or "with")
                if ':' in potential_title:
                    parts = potential_title.split(':', 1)
                    metadata['title'] = parts[0].strip().title()
                    metadata['subtitle'] = parts[1].strip().title()
                elif ' with ' in potential_title:
                    parts = potential_title.split(' with ', 1)
                    metadata['title'] = parts[0].strip().title()
                    metadata['subtitle'] = parts[1].strip().title()
                else:
                    metadata['title'] = potential_title.title()
                break
        
        return metadata
    
    def get_transcription_for_audiobook(self, folder_path: str) -> Dict:
        """
        Main method to get transcription and metadata for an audiobook
        Returns dict with transcription, metadata, and analysis info
        """
        print(f"[TRANSCRIBER] Analyzing audiobook: {folder_path}")
        
        # Analyze structure
        structure = self.detect_audiobook_structure(folder_path)
        print(f"[TRANSCRIBER] Structure type: {structure['type']}")
        
        transcription_result = {
            'structure': structure,
            'transcription': None,
            'metadata': None,
            'source_info': None,
            'success': False
        }
        
        try:
            audio_segment = None
            
            if structure['type'] == 'no_audio':
                print("[TRANSCRIBER] No audio files found")
                return transcription_result
            
            elif structure['type'] == 'single_file_with_chapters':
                # Extract first chapter
                primary_file = structure['primary_file']
                chapters = self.get_chapters_ffprobe(primary_file)
                
                if chapters:
                    first_chapter = chapters[0]
                    print(f"[TRANSCRIBER] Extracting first chapter: {first_chapter['title']} ({first_chapter['duration']:.1f}s)")
                    
                    audio_segment = self.extract_audio_segment(
                        primary_file, 
                        start_time=first_chapter['start'],
                        duration=min(first_chapter['duration'], self.default_duration)
                    )
                    
                    transcription_result['source_info'] = {
                        'source': 'first_chapter',
                        'file': str(primary_file),
                        'chapter_title': first_chapter['title'],
                        'duration': min(first_chapter['duration'], self.default_duration)
                    }
                else:
                    # Fallback to beginning of file
                    audio_segment = self.extract_audio_segment(primary_file, duration=self.default_duration)
                    transcription_result['source_info'] = {
                        'source': 'file_beginning',
                        'file': str(primary_file),
                        'duration': self.default_duration
                    }
            
            elif structure['type'] == 'single_file_no_chapters':
                # Extract beginning of single file
                primary_file = structure['primary_file']
                print(f"[TRANSCRIBER] Extracting beginning of single file: {primary_file.name}")
                
                audio_segment = self.extract_audio_segment(primary_file, duration=self.default_duration)
                transcription_result['source_info'] = {
                    'source': 'file_beginning',
                    'file': str(primary_file),
                    'duration': self.default_duration
                }
            
            elif structure['type'] == 'multi_file':
                # Extract beginning of first file
                first_file = structure['first_file']
                print(f"[TRANSCRIBER] Extracting beginning of first file: {first_file.name}")
                
                audio_segment = self.extract_audio_segment(first_file, duration=self.default_duration)
                transcription_result['source_info'] = {
                    'source': 'first_file',
                    'file': str(first_file),
                    'duration': self.default_duration
                }
            
            # Transcribe the extracted audio
            if audio_segment:
                print(f"[TRANSCRIBER] Transcribing audio segment: {audio_segment}")
                transcription = self.transcribe_audio(audio_segment)
                
                if transcription:
                    transcription_result['transcription'] = transcription
                    transcription_result['metadata'] = self.extract_metadata_from_transcription(transcription)
                    transcription_result['success'] = True
                    
                    print(f"[TRANSCRIBER] Transcription successful!")
                    print(f"[TRANSCRIBER] Extracted metadata: {transcription_result['metadata']}")
                else:
                    print("[TRANSCRIBER] Transcription failed")
            else:
                print("[TRANSCRIBER] Could not extract audio segment")
        
        except Exception as e:
            print(f"[TRANSCRIBER] Error during transcription: {e}")
        
        finally:
            # Clean up temporary files
            self.cleanup_temp_files()
        
        return transcription_result


# Convenience function for integration with audible service
def get_transcription_metadata(folder_path: str) -> Dict:
    """
    Convenience function to get transcription metadata for an audiobook folder
    Returns extracted metadata that can be used by the audible service
    """
    transcriber = AudiobookTranscriber()
    result = transcriber.get_transcription_for_audiobook(folder_path)
    
    if result['success'] and result['metadata']:
        return {
            'transcription_available': True,
            'transcription_metadata': result['metadata'],
            'transcription_source': result['source_info'],
            'raw_transcription': result['transcription']
        }
    else:
        return {
            'transcription_available': False,
            'error': 'Transcription failed or no metadata extracted'
        }


if __name__ == "__main__":
    # Test the transcriber
    test_folder = "Z:/Media"  # Adjust path as needed
    transcriber = AudiobookTranscriber()
    
    # Check dependencies
    transcriber.check_dependencies()
    
    # Test with a specific audiobook folder
    # result = transcriber.get_transcription_for_audiobook(test_folder)
    # print(json.dumps(result, indent=2))
