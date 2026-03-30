"""
Recreation Inventory Management System
--------------------------------------
config.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Python Configuration
PYTHON_PATH = os.getenv(
    "PYTHON_PATH", r"C:\Users\arthur.belanger\AppData\Local\anaconda3\python.exe"
)

# Application Paths
APP_ROOT = Path(__file__).parent.absolute()
DATA_DIR = os.getenv("DATA_DIR", str(APP_ROOT / "data"))
LOGS_DIR = os.getenv("LOGS_DIR", str(APP_ROOT / "logs"))
BACKUP_DIR = os.getenv("BACKUP_DIR", str(APP_ROOT / "backups"))

# Create necessary directories
Path(DATA_DIR).mkdir(exist_ok=True)
Path(LOGS_DIR).mkdir(exist_ok=True)
Path(BACKUP_DIR).mkdir(exist_ok=True)

# Database Configuration
DB_PATH = os.getenv("DB_PATH", str(Path(DATA_DIR) / "inventory.db"))

# Admin User Configuration
DEFAULT_ADMIN = {
    "username": os.getenv("ADMIN_USERNAME", "admin"),
    "password": os.getenv(
        "ADMIN_PASSWORD", "Admin@123!"
    ),  # More secure default password
    "first_name": os.getenv("ADMIN_FIRST_NAME", "Admin"),
    "last_name": os.getenv("ADMIN_LAST_NAME", "User"),
}

# Security Configuration
PASSWORD_EXPIRY_DAYS = int(
    os.getenv("PASSWORD_EXPIRY_DAYS", "60")
)  # Reduced from 90 to 60 days
MIN_PASSWORD_LENGTH = int(
    os.getenv("MIN_PASSWORD_LENGTH", "12")
)  # Increased from 8 to 12 characters
PASSWORD_HISTORY_LIMIT = int(
    os.getenv("PASSWORD_HISTORY_LIMIT", "10")
)  # Increased from 5 to 10
SESSION_EXPIRY_HOURS = int(
    os.getenv("SESSION_EXPIRY_HOURS", "12")
)  # Reduced from 24 to 12 hours

# Application Configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ALLOWED_EXTENSIONS = set(
    os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,pdf").split(",")
)  # Removed potentially dangerous formats
MAX_UPLOAD_SIZE_MB = int(
    os.getenv("MAX_UPLOAD_SIZE_MB", "5")
)  # Reduced from 10MB to 5MB

# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    "employee": 1,
    "manager": 2,
    "admin": 3,
    "recreation_supervisor": 3,  # Same level as admin
}

# Category and Location Lists
CATEGORIES = [
    "Weights",
    "Barbells",
    "Dumbbells",
    "Racks/Benches/Pins",
    "Safety Equipment",
    "Fitness Equipment",
    "Boxing Equipment",
    "Bands/Medicine Balls",
    "Jerseys/Shorts",
    "Outdoor Sports",
    "Indoor Sports",
    "Monitoring/Time Equipment",
    "Other",
]

LOCATIONS = [
    "6H108 - Music Room",
    "6G100 - Gym",
    "6G101 - Large Weight Room",
    "6G102 - Small Weight Room",
    "6G104 - Recreation Worker Equipment Booth",
    "6G107 - Recreation Equipment Storage Closet",
    "6G108 - Supply Closet",
    "6JA11 - Cleaning Closet",
    "Outside Storage Room",
    "Outside Shack",
]

# Condition colors for UI
CONDITION_COLORS = {
    "Excellent": "#28a745",  # Green
    "Good": "#17a2b8",  # Blue
    "Fair": "#ffc107",  # Yellow
    "Poor": "#dc3545",  # Red
    "Need for order": "#9932CC",  # Purple
    "Unknown": "#6c757d",  # Gray
}

# Optional Email Configuration
EMAIL_CONFIG = {
    "smtp_host": os.getenv("SMTP_HOST"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_username": os.getenv("SMTP_USERNAME"),
    "smtp_password": os.getenv("SMTP_PASSWORD"),
    "from_email": os.getenv("SMTP_FROM_EMAIL"),
}
