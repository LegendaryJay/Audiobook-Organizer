"""
Migration script to update existing metadata files from "old" to "original" structure
"""

import json
from pathlib import Path

def migrate_metadata_files():
    """Migrate all existing metadata files to the new structure"""
    metadata_dir = Path('./metadata')
    
    if not metadata_dir.exists():
        print("No metadata directory found.")
        return
    
    # Get all JSON files except tracking_summary
    metadata_files = [f for f in metadata_dir.glob('*.json') 
                     if f.name != 'tracking_summary.json']
    
    print(f"Found {len(metadata_files)} metadata files to migrate")
    
    migrated_count = 0
    for metadata_file in metadata_files:
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it needs migration
            if 'old' in data and 'original' not in data:
                print(f"Migrating {metadata_file.name}...")
                
                # Migrate structure
                new_data = {
                    'original': data['old'],
                    'audible_suggestions': [],
                    'status': data.get('status', 'pending')
                }
                
                # Remove old 'new' field if it exists
                if 'new' in data and data['new']:
                    # If there was data in 'new', add it as the first suggestion
                    new_data['audible_suggestions'].append({
                        **data['new'],
                        'match_score': 1.0,
                        'match_confidence': 'manual'
                    })
                
                # Save migrated data
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False)
                
                migrated_count += 1
            
            elif 'original' in data:
                print(f"Skipping {metadata_file.name} (already migrated)")
            
            else:
                print(f"Warning: {metadata_file.name} has unexpected structure")
        
        except Exception as e:
            print(f"Error migrating {metadata_file.name}: {e}")
    
    print(f"Migration completed! Migrated {migrated_count} files.")

if __name__ == '__main__':
    migrate_metadata_files()
