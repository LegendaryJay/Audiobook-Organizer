from audiobook_tracker import AudiobookTracker

tracker = AudiobookTracker('./metadata', './covers', 'Z:/Media')
cleanup_report = tracker.cleanup_orphaned_data(dry_run=True)

print(f"Would remove {cleanup_report['orphaned_metadata_count']} metadata files")
print(f"Would remove {cleanup_report['orphaned_covers_count']} cover files")

# Show status report
report = tracker.get_scan_report()
print(f"\nTracking Status:")
print(f"  Last scan: {report['last_scan']}")
print(f"  Current audiobooks: {report['audiobooks_tracked']}")
print(f"  Current audio files: {report['current_audio_files']}")
print(f"  Orphaned metadata: {report['orphaned_metadata']}")
print(f"  Orphaned covers: {report['orphaned_covers']}")
print(f"  Needs cleanup: {report['needs_cleanup']}")
