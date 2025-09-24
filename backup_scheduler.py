"""
Recreation Inventory Management System
-----------------------------------------
backup_scheduler.py file for Streamlit UI
-----------------------------------------
Author: github/musicalviking
"""

import os
import shutil
import time
import sqlite3
import schedule
import threading
from pathlib import Path
from datetime import datetime, timedelta
import logging
import zipfile

from logging_config import get_logger

logger = get_logger(__name__)


class BackupManager:
    def __init__(
        self, db_path=None, backup_dir=None, max_backups=30, backup_interval_hours=24
    ):
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
        self.backup_interval_hours = backup_interval_hours
        self.running = False
        self.scheduler_thread = None
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

            # Create database connection and backup
            try:
                # Try to use SQLite backup API for more reliable backups
                source = sqlite3.connect(self.db_path)
                dest = sqlite3.connect(backup_path)
                source.backup(dest)
                dest.close()
                source.close()
            except (sqlite3.Error, AttributeError):
                # Fallback to file copy if backup API is not available
                logger.warning(
                    "Using file copy for backup instead of SQLite backup API"
                )
                shutil.copy2(self.db_path, backup_path)

            # Create a ZIP file of the backup for compression
            zip_filename = f"{os.path.splitext(backup_filename)[0]}.zip"
            zip_path = os.path.join(self.backup_dir, zip_filename)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, os.path.basename(backup_path))

            # Remove the uncompressed backup file to save space
            os.remove(backup_path)

            logger.info(f"Database backup created: {zip_path}")
            self.clean_old_backups()
            return zip_path

        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None

    def clean_old_backups(self):
        """Remove old backups exceeding max_backups"""
        try:
            # Get all backup files (both .db and .zip)
            backup_files = []
            for ext in [".db", ".zip"]:
                pattern = f"*_backup_*{ext}"
                backup_files.extend(list(Path(self.backup_dir).glob(pattern)))

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
            # Stop the scheduler during restore
            self.stop_scheduler()

            # Handle zip files
            if backup_path.endswith(".zip"):
                # Extract the .db file from the zip
                with zipfile.ZipFile(backup_path, "r") as zipf:
                    # Get the .db filename from within the zip
                    db_files = [f for f in zipf.namelist() if f.endswith(".db")]
                    if not db_files:
                        logger.error(
                            f"No database file found in backup zip: {backup_path}"
                        )
                        return False

                    # Create a temporary directory for extraction
                    temp_dir = os.path.join(self.backup_dir, "temp_extract")
                    os.makedirs(temp_dir, exist_ok=True)

                    # Extract the first db file
                    zipf.extract(db_files[0], temp_dir)
                    extracted_path = os.path.join(temp_dir, db_files[0])

                    # Restore from the extracted file
                    shutil.copy2(extracted_path, self.db_path)

                    # Clean up
                    os.remove(extracted_path)
                    os.rmdir(temp_dir)
            else:
                # Direct restore from .db file
                shutil.copy2(backup_path, self.db_path)

            logger.info(f"Database restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False
        finally:
            # Restart the scheduler
            self.start_scheduler()

    def get_available_backups(self):
        """Get a list of available backups with their details"""
        backups = []
        try:
            # Look for both .db and .zip backups
            for ext in [".db", ".zip"]:
                pattern = f"*_backup_*{ext}"
                backup_files = list(Path(self.backup_dir).glob(pattern))

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

    def _backup_job(self):
        """Scheduled backup job"""
        logger.info("Running scheduled backup job")
        self.create_backup()

    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        schedule.every(self.backup_interval_hours).hours.do(self._backup_job)

        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def start_scheduler(self):
        """Start the backup scheduler"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            logger.info(
                f"Backup scheduler started (every {self.backup_interval_hours} hours)"
            )

    def stop_scheduler(self):
        """Stop the backup scheduler"""
        if self.running:
            self.running = False
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=2)
            logger.info("Backup scheduler stopped")


# Singleton instance for the application
_backup_manager = None


def get_backup_manager():
    """Get the backup manager singleton instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


# Start the backup scheduler when this module is imported
def init_backup_scheduler():
    """Initialize and start the backup scheduler"""
    backup_manager = get_backup_manager()
    backup_manager.start_scheduler()
    return backup_manager
