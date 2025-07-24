from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
import threading
from pathlib import Path
from metadata_extractor import process_all_audiobooks, process_specific_folders
from polling_watcher import start_file_watcher_safe
from audiobook_tracker import AudiobookTracker
from audible_service import AudibleSearchService
from path_generator import generate_paths_for_audiobook, preview_organization

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
METADATA_DIR = Path('./metadata')
COVERS_DIR = Path('./covers')
MEDIA_ROOT = 'Z:/Media'  # Production directory
STATUS_OPTIONS = ['pending', 'accepted', 'ignored', 'broken', 'manual']

# Ensure directories exist
METADATA_DIR.mkdir(exist_ok=True)
COVERS_DIR.mkdir(exist_ok=True)

# Initialize tracker and Audible service
tracker = AudiobookTracker(METADATA_DIR, COVERS_DIR, MEDIA_ROOT)
audible_service = AudibleSearchService(COVERS_DIR)

# Root endpoint for API info
@app.route('/')
def root():
    return jsonify({
        'message': 'Audiobook Organizer API is running',
        'endpoints': {
            'audiobooks': '/api/audiobooks',
            'scan': '/api/scan',
            'status': '/api/status',
            'cleanup': '/api/cleanup',
            'orphaned': '/api/orphaned',
            'audible': '/api/audible/<uuid>',
            'paths': '/api/audiobooks/<uuid>/paths',
            'preview': '/api/audiobooks/<uuid>/preview',
            'purge': '/api/purge',
            'covers': '/covers/<filename>'
        }
    })

# Paginated audiobooks endpoint
@app.route('/api/audiobooks')
def get_audiobooks():
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 10))
        
        if offset < 0:
            offset = 0
        if limit <= 0:
            limit = 10
        
        # Get all metadata files
        metadata_files = list(METADATA_DIR.glob('*.json'))
        # Filter out tracking summary
        metadata_files = [f for f in metadata_files if f.name != 'tracking_summary.json']
        total = len(metadata_files)
        
        # Load paginated items
        items = []
        for metadata_file in metadata_files[offset:offset+limit]:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items.append(data)
            except Exception as e:
                print(f"Error loading {metadata_file}: {e}")
                continue
        
        return jsonify({'total': total, 'items': items})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update audiobook status
@app.route('/api/audiobooks/<int:index>/status', methods=['POST'])
def update_status(index):
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in STATUS_OPTIONS:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Get metadata files
        metadata_files = sorted([f for f in METADATA_DIR.glob('*.json') if f.name != 'tracking_summary.json'])
        
        if index >= len(metadata_files):
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        # Update the metadata file
        metadata_file = metadata_files[index]
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        metadata['status'] = status
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Update audiobook status by UUID
@app.route('/api/audiobooks/<uuid_str>/status', methods=['POST'])
def update_status_by_uuid(uuid_str):
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in STATUS_OPTIONS:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Find the metadata file by UUID
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'success': False, 'error': 'Audiobook not found'}), 404
        
        # Update the metadata file
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        metadata['status'] = status
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Trigger manual scan
@app.route('/api/scan', methods=['POST'])
def scan_library():
    try:
        data = request.get_json() or {}
        force_full_scan = data.get('full_scan', False)
        
        if force_full_scan:
            # Force full scan of all files
            print("Performing full library scan...")
            count = process_all_audiobooks(MEDIA_ROOT)
        else:
            # Intelligent scan - only new/changed folders
            folders_to_scan, current_folders = tracker.get_folders_to_scan()
            if folders_to_scan:
                print(f"Scanning {len(folders_to_scan)} changed folders...")
                count = process_specific_folders(MEDIA_ROOT, folders_to_scan)
            else:
                print("No changes detected.")
                count = 0
        
        # Update tracking summary after scan
        tracker.update_tracking_after_scan(count)
        return jsonify({'success': True, 'count': count, 'full_scan': force_full_scan})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Serve cover images
@app.route('/covers/<filename>')
def serve_cover(filename):
    try:
        return send_from_directory(COVERS_DIR, filename)
    except FileNotFoundError:
        return jsonify({'error': 'Cover not found'}), 404

# Get tracking status and cleanup report
@app.route('/api/status')
def get_status():
    try:
        report = tracker.get_scan_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cleanup orphaned metadata and covers
@app.route('/api/cleanup', methods=['POST'])
def cleanup_orphaned():
    try:
        data = request.get_json() or {}
        dry_run = data.get('dry_run', True)
        
        cleanup_report = tracker.cleanup_orphaned_data(dry_run=dry_run)
        return jsonify(cleanup_report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get list of orphaned items
@app.route('/api/orphaned')
def get_orphaned():
    try:
        orphaned_metadata, orphaned_covers = tracker.find_orphaned_metadata()
        return jsonify({
            'orphaned_metadata': [
                {
                    'uuid': item['uuid'],
                    'title': item['title'],
                    'paths': item['paths'],
                    'file': item['metadata_file'].name
                } for item in orphaned_metadata
            ],
            'orphaned_covers': [str(cover.name) for cover in orphaned_covers]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Placeholder for apply endpoint
@app.route('/api/audiobooks/<int:index>/apply', methods=['POST'])
def apply_changes(index):
    # TODO: Move/rename file, update metadata, backup changes
    return jsonify({'success': True, 'message': 'Apply not yet implemented.'})

# Generate organized paths for audiobook
@app.route('/api/audiobooks/<uuid_str>/paths', methods=['POST'])
def generate_audiobook_paths_endpoint(uuid_str):
    """Generate organized file paths for an audiobook based on selected Audible suggestion"""
    try:
        # Find the metadata file
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'error': 'Audiobook not found'}), 404
        
        # Load current metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            audiobook_data = json.load(f)
        
        # Get the selected audible ID and find the corresponding suggestion index
        selected_audible_id = audiobook_data.get('selected_audible_id', 1)
        audible_suggestions = audiobook_data.get('audible_suggestions', [])
        
        # Find the suggestion with the selected ID
        selected_suggestion_index = 0  # Default to first
        for i, suggestion in enumerate(audible_suggestions):
            if suggestion.get('id') == selected_audible_id:
                selected_suggestion_index = i
                break
        
        # Generate organized paths using the path generator
        path_result = generate_paths_for_audiobook(audiobook_data, selected_suggestion_index)
        
        if not path_result:
            return jsonify({
                'success': False,
                'error': 'Could not generate organized paths',
                'message': 'Path generation failed or invalid data'
            }), 400
        
        return jsonify({
            'success': True,
            'paths': path_result
        })
    
    except Exception as e:
        print(f"[ERROR] Path generation failed: {e}")
        return jsonify({'error': f'Path generation failed: {str(e)}'}), 500

# Preview audiobook organization
@app.route('/api/audiobooks/<uuid_str>/preview', methods=['POST'])
def preview_audiobook_paths(uuid_str):
    """Preview how an audiobook would be organized"""
    try:
        # Find the metadata file
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'error': 'Audiobook not found'}), 404
        
        # Load current metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            audiobook_data = json.load(f)
        
        # Get the selected audible ID and find the corresponding suggestion index
        selected_audible_id = audiobook_data.get('selected_audible_id', 1)
        audible_suggestions = audiobook_data.get('audible_suggestions', [])
        
        # Find the suggestion with the selected ID
        selected_suggestion_index = 0  # Default to first
        for i, suggestion in enumerate(audible_suggestions):
            if suggestion.get('id') == selected_audible_id:
                selected_suggestion_index = i
                break
        
        # Generate preview using the path generator
        preview_text = preview_organization(audiobook_data, selected_suggestion_index)
        
        return jsonify({
            'success': True,
            'preview': preview_text
        })
    
    except Exception as e:
        print(f"[ERROR] Preview generation failed: {e}")
        return jsonify({'error': f'Preview generation failed: {str(e)}'}), 500

# Enhance audiobook with Audible search
@app.route('/api/audible/<uuid_str>', methods=['POST'])
def enhance_with_audible(uuid_str):
    """Manually enhance an audiobook with Audible search"""
    try:
        # Find the metadata file
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'error': 'Audiobook not found'}), 404
        
        # Load current metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_metadata = data.get('original', {})
        if not original_metadata:
            return jsonify({'error': 'Invalid metadata structure'}), 400
        
        # Enhance with Audible
        print(f"[API] Manual Audible enhancement requested for: {original_metadata.get('title', 'Unknown')}")
        
        enhancement_result = audible_service.enhance_audiobook_metadata(original_metadata, uuid_str)
        
        if enhancement_result.get('audible_enhanced'):
            # Update the metadata file with new suggestions
            suggestions = enhancement_result.get('audible_suggestions', [])
            
            # Generate paths for each suggestion
            for suggestion in suggestions:
                try:
                    temp_audiobook_data = {
                        'original': original_metadata,
                        'audible_suggestions': [suggestion]
                    }
                    path_result = generate_paths_for_audiobook(temp_audiobook_data, 0)
                    if path_result and path_result.get('organized_paths'):
                        suggestion['paths'] = path_result['organized_paths']
                    else:
                        suggestion['paths'] = original_metadata.get('paths', [])
                except Exception as e:
                    print(f"[AUDIBLE_ENHANCE] Warning: Could not generate paths for suggestion {suggestion.get('id', 'unknown')}: {e}")
                    suggestion['paths'] = original_metadata.get('paths', [])
            
            data['audible_suggestions'] = suggestions
            data['selected_audible_id'] = enhancement_result.get('selected_audible_id', 1)  # Set default selection
            data['audible_last_search'] = enhancement_result.get('message', '')
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': f"Found {len(data['audible_suggestions'])} suggestions",
                'suggestions_count': len(data['audible_suggestions']),
                'selected_audible_id': data['selected_audible_id'],
                'audible_suggestions': data['audible_suggestions']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No Audible results found',
                'error': enhancement_result.get('message', 'Search failed')
            })
    
    except Exception as e:
        print(f"[ERROR] Audible enhancement failed: {e}")
        return jsonify({'error': f'Enhancement failed: {str(e)}'}), 500

# Manual audible search with custom query
@app.route('/api/audiobooks/<uuid_str>/manual-search', methods=['POST'])
def manual_audible_search(uuid_str):
    """Perform manual audible search with custom query"""
    try:
        data = request.get_json()
        search_query = data.get('query', '').strip()
        
        if not search_query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Find the metadata file
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'error': 'Audiobook not found'}), 404
        
        # Load current metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"[DEBUG] Loaded metadata keys: {list(metadata.keys())}")
        print(f"[DEBUG] Has 'original' key: {'original' in metadata}")
        
        original_metadata = metadata.get('original', {})
        print(f"[DEBUG] Original metadata: {bool(original_metadata)}")
        
        if not original_metadata:
            print(f"[ERROR] Invalid metadata structure for {uuid_str}")
            print(f"[ERROR] Metadata content: {metadata}")
            return jsonify({'error': 'Invalid metadata structure'}), 400
        
        print(f"[API] Manual Audible search requested for: {original_metadata.get('title', 'Unknown')} with query: '{search_query}'")
        
        # Create a search query dict for the audible service
        search_data = {
            'asin': '',  # No ASIN for manual search
            'title': search_query,  # Use the manual query as title
            'author': '',  # No specific author for manual search
            'filename': original_metadata.get('paths', [''])[0] if original_metadata.get('paths') else ''
        }
        
        # Use the audible service to search with the manual query
        search_results = audible_service.search_audible(search_data)
        
        if not search_results:
            return jsonify({
                'success': False,
                'message': 'No results found for manual search',
                'error': 'No search results'
            })
        
        # Rank results and extract metadata like normal audible enhancement
        ranked_results = audible_service.rank_search_results(search_results, original_metadata)
        
        # Extract metadata for top matches
        suggestions = []
        for i, (audible_meta, score) in enumerate(ranked_results[:10]):
            enhanced_meta = audible_service.extract_audible_metadata_basic(audible_meta, uuid_str)
            enhanced_meta['id'] = i + 1
            enhanced_meta['match_score'] = score
            enhanced_meta['match_confidence'] = 'high' if score > 0.8 else 'medium' if score > 0.5 else 'low'
            
            # Generate paths for this suggestion
            try:
                temp_audiobook_data = {
                    'original': original_metadata,
                    'audible_suggestions': [enhanced_meta]
                }
                path_result = generate_paths_for_audiobook(temp_audiobook_data, 0)
                if path_result and path_result.get('organized_paths'):
                    enhanced_meta['paths'] = path_result['organized_paths']
                else:
                    enhanced_meta['paths'] = original_metadata.get('paths', [])
            except Exception as e:
                print(f"[MANUAL_SEARCH] Warning: Could not generate paths: {e}")
                enhanced_meta['paths'] = original_metadata.get('paths', [])
            
            suggestions.append(enhanced_meta)
        
        # Enhance the best match with book number info
        if suggestions:
            best_match = suggestions[0]
            enhanced_best = audible_service.enhance_with_book_number(ranked_results[0][0], best_match)
            suggestions[0] = enhanced_best
        
        # Update the metadata file
        metadata['audible_suggestions'] = suggestions
        metadata['selected_audible_id'] = 1  # Default to first result
        metadata['audible_last_search'] = f'Manual search: "{search_query}" - Found {len(suggestions)} results'
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': f'Manual search found {len(suggestions)} results',
            'audible_suggestions': suggestions,
            'selected_audible_id': 1,
            'search_query': search_query
        })
    
    except Exception as e:
        print(f"[ERROR] Manual search failed: {e}")
        return jsonify({'error': f'Manual search failed: {str(e)}'}), 500

# Update selected audible suggestion
@app.route('/api/audiobooks/<uuid_str>/select-audible', methods=['POST'])
def select_audible_suggestion(uuid_str):
    """Update which audible suggestion is selected for an audiobook"""
    try:
        data = request.get_json()
        selected_id = data.get('selected_id')
        
        if not isinstance(selected_id, int) or selected_id < 1:
            return jsonify({'error': 'Invalid selected_id. Must be a positive integer'}), 400
        
        # Find the metadata file
        metadata_file = METADATA_DIR / f"{uuid_str}.json"
        if not metadata_file.exists():
            return jsonify({'error': 'Audiobook not found'}), 404
        
        # Load current metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if the selected ID exists in audible suggestions
        audible_suggestions = metadata.get('audible_suggestions', [])
        if not audible_suggestions:
            return jsonify({'error': 'No audible suggestions available'}), 400
        
        # Find suggestion with the requested ID
        selected_suggestion = None
        for suggestion in audible_suggestions:
            if suggestion.get('id') == selected_id:
                selected_suggestion = suggestion
                break
        
        if not selected_suggestion:
            return jsonify({'error': f'No suggestion found with ID {selected_id}'}), 400
        
        # Update the selected audible ID
        metadata['selected_audible_id'] = selected_id
        
        # Save the updated metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"[API] Updated selected audible ID to {selected_id} for {metadata.get('original', {}).get('title', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'selected_id': selected_id,
            'selected_suggestion': selected_suggestion
        })
    
    except Exception as e:
        print(f"[ERROR] Failed to update selected audible: {e}")
        return jsonify({'error': f'Failed to update selection: {str(e)}'}), 500

# Bulk Audible enhancement
@app.route('/api/audible/bulk', methods=['POST'])
def bulk_enhance_audible():
    """Enhance multiple audiobooks with Audible search"""
    try:
        request_data = request.get_json() or {}
        force_refresh = request_data.get('force_refresh', False)
        limit = int(request_data.get('limit', 10))  # Limit to prevent overload
        
        # Get all metadata files
        metadata_files = [f for f in METADATA_DIR.glob('*.json') 
                         if f.name != 'tracking_summary.json']
        
        processed = 0
        enhanced = 0
        errors = []
        
        for metadata_file in metadata_files[:limit]:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Skip if already has suggestions and not forcing refresh
                if not force_refresh and data.get('audible_suggestions'):
                    continue
                
                original_metadata = data.get('original', {})
                if not original_metadata:
                    continue
                
                uuid_str = original_metadata.get('uuid', metadata_file.stem)
                print(f"[BULK] Enhancing: {original_metadata.get('title', 'Unknown')}")
                
                enhancement_result = audible_service.enhance_audiobook_metadata(original_metadata, uuid_str)
                
                if enhancement_result.get('audible_enhanced'):
                    data['audible_suggestions'] = enhancement_result.get('audible_suggestions', [])
                    data['audible_last_search'] = enhancement_result.get('message', '')
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    enhanced += 1
                
                processed += 1
                
            except Exception as e:
                errors.append(f"{metadata_file.name}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'processed': processed,
            'enhanced': enhanced,
            'errors': errors,
            'message': f"Enhanced {enhanced} of {processed} audiobooks"
        })
    
    except Exception as e:
        return jsonify({'error': f'Bulk enhancement failed: {str(e)}'}), 500

def initialize_app():
    """Initialize the application"""
    print("Starting Audiobook Organizer Backend...")
    
    # Start file watcher in background thread with error handling
    try:
        watcher_thread = threading.Thread(target=start_file_watcher_safe, args=(MEDIA_ROOT,), daemon=True)
        watcher_thread.start()
    except Exception as e:
        print(f"Warning: Could not start file watcher: {e}")
        print("File watching disabled - you can manually scan via the API.")
    
    # Intelligent scan - only process new/changed folders
    print("Checking for changes...")
    try:
        folders_to_scan, current_folders = tracker.get_folders_to_scan()
        
        if folders_to_scan:
            print(f"Found {len(folders_to_scan)} folders that need scanning...")
            count = process_specific_folders(MEDIA_ROOT, folders_to_scan)
            print(f"Processed {count} new/changed audiobooks.")
        else:
            print("No changes detected - all audiobooks are up to date.")
            count = 0
        
        # Update tracking summary after scan
        tracker.update_tracking_after_scan(count)
        
        # Show total status
        summary = tracker.load_summary()
        total_tracked = summary.get('audiobook_count', 0)
        print(f"Total audiobooks tracked: {total_tracked}")
        
    except Exception as e:
        print(f"Error during intelligent scan: {e}")
        print("Falling back to full scan...")
        try:
            count = process_all_audiobooks(MEDIA_ROOT)
            tracker.update_tracking_after_scan(count)
            print(f"Full scan complete. Found {count} audiobooks.")
        except Exception as e2:
            print(f"Error during full scan: {e2}")
    
    # Check for orphaned data
    try:
        report = tracker.get_scan_report()
        if report['needs_cleanup']:
            print(f"⚠️  Found {report['orphaned_metadata']} orphaned metadata files and {report['orphaned_covers']} orphaned covers")
            print("   Use /api/cleanup endpoint to clean up orphaned data")
    except Exception as e:
        print(f"Error checking for orphaned data: {e}")

# Purge all data and regenerate
@app.route('/api/purge', methods=['POST'])
def purge_and_regenerate():
    """Delete all metadata and covers, then regenerate everything from scratch"""
    try:
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'error': 'Confirmation required',
                'message': 'Set "confirm": true to proceed with purge'
            }), 400
        
        print("[PURGE] Starting purge and regeneration process...")
        
        # Count existing files before deletion
        metadata_count = len([f for f in METADATA_DIR.glob('*.json') if f.name != 'tracking_summary.json'])
        cover_count = len(list(COVERS_DIR.glob('*')))
        
        # Delete all metadata files (except tracking summary)
        deleted_metadata = 0
        for metadata_file in METADATA_DIR.glob('*.json'):
            if metadata_file.name != 'tracking_summary.json':
                try:
                    metadata_file.unlink()
                    deleted_metadata += 1
                except Exception as e:
                    print(f"[PURGE] Warning: Could not delete {metadata_file}: {e}")
        
        # Delete all cover files
        deleted_covers = 0
        for cover_file in COVERS_DIR.glob('*'):
            try:
                cover_file.unlink()
                deleted_covers += 1
            except Exception as e:
                print(f"[PURGE] Warning: Could not delete {cover_file}: {e}")
        
        # Delete tracking summary to force full regeneration
        tracking_summary = METADATA_DIR / 'tracking_summary.json'
        if tracking_summary.exists():
            try:
                tracking_summary.unlink()
                print("[PURGE] Deleted tracking summary")
            except Exception as e:
                print(f"[PURGE] Warning: Could not delete tracking summary: {e}")
        
        print(f"[PURGE] Deleted {deleted_metadata} metadata files and {deleted_covers} cover files")
        
        # Regenerate everything from scratch
        print("[PURGE] Starting full regeneration...")
        try:
            count = process_all_audiobooks(MEDIA_ROOT)
            tracker.update_tracking_after_scan(count)
            print(f"[PURGE] Regenerated {count} audiobooks")
            
            return jsonify({
                'success': True,
                'message': f'Purge complete. Deleted {deleted_metadata} metadata files and {deleted_covers} covers. Regenerated {count} audiobooks.',
                'deleted': {
                    'metadata': deleted_metadata,
                    'covers': deleted_covers
                },
                'regenerated': count
            })
            
        except Exception as e:
            print(f"[PURGE] Error during regeneration: {e}")
            return jsonify({
                'success': False,
                'error': f'Purge completed but regeneration failed: {str(e)}',
                'deleted': {
                    'metadata': deleted_metadata,
                    'covers': deleted_covers
                }
            }), 500
    
    except Exception as e:
        print(f"[PURGE] Error during purge: {e}")
        return jsonify({'error': f'Purge failed: {str(e)}'}), 500

# Test series info endpoint
@app.route('/api/test-series', methods=['POST'])
def test_series():
    try:
        data = request.get_json()
        title = data.get('title', '')
        author = data.get('author', '')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Test the series service
        if hasattr(audible_service, 'series_service') and audible_service.series_service:
            series_info = audible_service.series_service.find_book_series_info(title, author)
            return jsonify(series_info)
        else:
            return jsonify({'error': 'Series service not available'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    initialize_app()
    print("Audiobook backend running on http://localhost:4000")
    app.run(host='0.0.0.0', port=4000, debug=False)
