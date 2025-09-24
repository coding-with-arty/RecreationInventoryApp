"""
Recreation Inventory Management System
--------------------------------------
simple_backup.py file for Streamlit UI
--------------------------------------
Author: github/musicalviking
"""

import os
import shutil
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
import logging

from logging_config import get_logger

logger = get_logger(__name__)


class SimpleBackupManager:
    """Simplified backup manager that doesn't require the schedule package"""

    def __init__(self, db_path=None, backup_dir=None, max_backups=10):
        # Use environment variables or default paths
        self.db_path = db_path or os.getenv("DB_PATH", "inventory.db")
        self.backup_dir = backup_dir or os.getenv("BACKUP_DIR", "backups")

        # Ensure paths are absolute
        if not os.path.isabs(self.db_path):
            self.db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), self.db_path
            )

        if not os.path.isabs(self.backup_dir):
            self.backup_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), self.backup_dir
            )

        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)

        self.max_backups = max_backups
        self.last_backup_time = None
        logger.info(
            f"Backup Manager initialized with db_path={self.db_path}, backup_dir={self.backup_dir}"
        )

    def create_backup(self):
        """Create a backup of the database with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_filename = os.path.basename(self.db_path)
            backup_filename = (
                f"{os.path.splitext(db_filename)[0]}_backup_{timestamp}.db"
            )
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Check if source database exists
            if not os.path.exists(self.db_path):
                logger.error(f"Database file not found at {self.db_path}")
                return None

            # Create database backup using file copy
            shutil.copy2(self.db_path, backup_path)

            self.last_backup_time = datetime.now()
            logger.info(f"Database backup created: {backup_path}")
            self.clean_old_backups()
            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None

    def clean_old_backups(self):
        """Remove old backups exceeding max_backups"""
        try:
            # Get all backup files
            backup_files = list(Path(self.backup_dir).glob("*_backup_*.db"))

            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime)

            # Delete oldest backups if we have too many
            if len(backup_files) > self.max_backups:
                for old_backup in backup_files[: -self.max_backups]:
                    os.remove(old_backup)
                    logger.info(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.error(f"Failed to clean old backups: {str(e)}")

    def restore_backup(self, backup_path):
        """Restore database from a backup file"""
        try:
            # Simple file copy restore
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False

    def get_available_backups(self):
        """Get a list of available backups with their details"""
        backups = []
        try:
            backup_files = list(Path(self.backup_dir).glob("*_backup_*.db"))

            for bf in backup_files:
                # Extract timestamp from filename
                timestamp_str = bf.stem.split("_backup_")[-1]
                try:
                    # Try to parse the timestamp
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    formatted_date = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_date = "Unknown date"

                # Get file size in KB or MB
                size_bytes = bf.stat().st_size
                if size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                backups.append(
                    {
                        "path": str(bf),
                        "filename": bf.name,
                        "date": formatted_date,
                        "size": size_str,
                        "timestamp": timestamp_str,
                    }
                )

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x["timestamp"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to get available backups: {str(e)}")

        return backups

    def should_backup(self, hours=24):
        """Check if it's time for a backup based on the last backup time"""
        if self.last_backup_time is None:
            return True

        time_since_backup = datetime.now() - self.last_backup_time
        return time_since_backup > timedelta(hours=hours)


# Singleton instance for the application
_backup_manager = None


def get_backup_manager():
    """Get the backup manager singleton instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = SimpleBackupManager()
    return _backup_manager
