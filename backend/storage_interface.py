"""
Storage Interface - Abstraction layer for audiobook tracking data
This allows easy migration from JSON to database when needed
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import sqlite3
from abc import ABC, abstractmethod


class StorageInterface(ABC):
    """Abstract interface for audiobook tracking storage"""
    
    @abstractmethod
    def get_tracking_data(self) -> Dict[str, Any]:
        """Get the complete tracking data"""
        pass
    
    @abstractmethod
    def update_folder_tracking(self, folder_path: str, files: list, file_count: int, last_modified: float):
        """Update tracking info for a specific folder"""
        pass
    
    @abstractmethod
    def remove_folder_tracking(self, folder_path: str):
        """Remove tracking for a folder"""
        pass
    
    @abstractmethod
    def get_folder_info(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """Get tracking info for a specific folder"""
        pass
    
    @abstractmethod
    def update_last_scan(self):
        """Update the last scan timestamp"""
        pass


class JsonStorage(StorageInterface):
    """JSON file-based storage implementation"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not self.file_path.exists():
            self._save_data({
                "last_scan": datetime.now().isoformat(),
                "tracked_folders": {}
            })
    
    def _load_data(self) -> Dict[str, Any]:
        with open(self.file_path, 'r') as f:
            return json.load(f)
    
    def _save_data(self, data: Dict[str, Any]):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_tracking_data(self) -> Dict[str, Any]:
        return self._load_data()
    
    def update_folder_tracking(self, folder_path: str, files: list, file_count: int, last_modified: float):
        data = self._load_data()
        data['tracked_folders'][folder_path] = {
            'files': files,
            'file_count': file_count,
            'last_modified': last_modified
        }
        self._save_data(data)
    
    def remove_folder_tracking(self, folder_path: str):
        data = self._load_data()
        if folder_path in data['tracked_folders']:
            del data['tracked_folders'][folder_path]
            self._save_data(data)
    
    def get_folder_info(self, folder_path: str) -> Optional[Dict[str, Any]]:
        data = self._load_data()
        return data['tracked_folders'].get(folder_path)
    
    def update_last_scan(self):
        data = self._load_data()
        data['last_scan'] = datetime.now().isoformat()
        self._save_data(data)


class SqliteStorage(StorageInterface):
    """SQLite database storage implementation (for future use)"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracking_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_folders (
                    folder_path TEXT PRIMARY KEY,
                    file_count INTEGER,
                    last_modified REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path TEXT,
                    file_name TEXT,
                    FOREIGN KEY (folder_path) REFERENCES tracked_folders (folder_path),
                    UNIQUE(folder_path, file_name)
                )
            """)
            
            # Set initial last_scan if not exists
            conn.execute("""
                INSERT OR IGNORE INTO tracking_meta (key, value)
                VALUES ('last_scan', ?)
            """, (datetime.now().isoformat(),))
    
    def get_tracking_data(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get last_scan
            last_scan = conn.execute(
                "SELECT value FROM tracking_meta WHERE key = 'last_scan'"
            ).fetchone()['value']
            
            # Get all folders with their files
            folders = {}
            folder_rows = conn.execute("""
                SELECT folder_path, file_count, last_modified 
                FROM tracked_folders
            """).fetchall()
            
            for folder_row in folder_rows:
                files = conn.execute("""
                    SELECT file_name FROM tracked_files 
                    WHERE folder_path = ?
                """, (folder_row['folder_path'],)).fetchall()
                
                folders[folder_row['folder_path']] = {
                    'files': [f['file_name'] for f in files],
                    'file_count': folder_row['file_count'],
                    'last_modified': folder_row['last_modified']
                }
            
            return {
                'last_scan': last_scan,
                'tracked_folders': folders
            }
    
    def update_folder_tracking(self, folder_path: str, files: list, file_count: int, last_modified: float):
        with sqlite3.connect(self.db_path) as conn:
            # Insert/update folder
            conn.execute("""
                INSERT OR REPLACE INTO tracked_folders 
                (folder_path, file_count, last_modified, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (folder_path, file_count, last_modified))
            
            # Delete old files for this folder
            conn.execute("DELETE FROM tracked_files WHERE folder_path = ?", (folder_path,))
            
            # Insert new files
            for file_name in files:
                conn.execute("""
                    INSERT INTO tracked_files (folder_path, file_name)
                    VALUES (?, ?)
                """, (folder_path, file_name))
    
    def remove_folder_tracking(self, folder_path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tracked_files WHERE folder_path = ?", (folder_path,))
            conn.execute("DELETE FROM tracked_folders WHERE folder_path = ?", (folder_path,))
    
    def get_folder_info(self, folder_path: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            folder = conn.execute("""
                SELECT file_count, last_modified FROM tracked_folders 
                WHERE folder_path = ?
            """, (folder_path,)).fetchone()
            
            if not folder:
                return None
            
            files = conn.execute("""
                SELECT file_name FROM tracked_files 
                WHERE folder_path = ?
            """, (folder_path,)).fetchall()
            
            return {
                'files': [f['file_name'] for f in files],
                'file_count': folder['file_count'],
                'last_modified': folder['last_modified']
            }
    
    def update_last_scan(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tracking_meta SET value = ? WHERE key = 'last_scan'
            """, (datetime.now().isoformat(),))


def create_storage(storage_type: str = "json", path: Optional[Path] = None) -> StorageInterface:
    """Factory function to create storage instance"""
    if storage_type == "json":
        return JsonStorage(path or Path("metadata/tracking_summary.json"))
    elif storage_type == "sqlite":
        return SqliteStorage(path or Path("metadata/tracking.db"))
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
