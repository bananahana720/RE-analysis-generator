#!/usr/bin/env python3
"""Log cleanup utility for Phoenix Real Estate project."""

import shutil
from pathlib import Path
from datetime import datetime


def cleanup_logs(logs_dir: Path, keep_recent: int = 5):
    """
    Clean up log directories, keeping only the most recent ones.
    
    Args:
        logs_dir: Path to logs directory
        keep_recent: Number of recent log directories to keep
    """
    if not logs_dir.exists():
        print(f"Logs directory {logs_dir} does not exist")
        return
    
    # Get all UUID-named directories (log sessions)
    log_dirs = []
    for item in logs_dir.iterdir():
        if item.is_dir() and len(item.name) == 36:  # UUID length
            try:
                # Get modification time
                mtime = item.stat().st_mtime
                log_dirs.append((item, mtime))
            except OSError:
                continue
    
    # Sort by modification time (newest first)
    log_dirs.sort(key=lambda x: x[1], reverse=True)
    
    # Keep only the most recent ones
    dirs_to_remove = log_dirs[keep_recent:]
    
    print(f"Found {len(log_dirs)} log directories")
    print(f"Keeping {min(len(log_dirs), keep_recent)} most recent")
    print(f"Removing {len(dirs_to_remove)} old directories")
    
    for log_dir, mtime in dirs_to_remove:
        try:
            shutil.rmtree(log_dir)
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Removed: {log_dir.name} (modified: {date_str})")
        except OSError as e:
            print(f"Error removing {log_dir.name}: {e}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    logs_directory = project_root / "logs"
    
    print("Phoenix Real Estate - Log Cleanup Utility")
    print("=" * 50)
    
    cleanup_logs(logs_directory, keep_recent=5)
    
    print("\nLog cleanup completed!")