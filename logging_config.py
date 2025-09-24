"""
Recreation Inventory Management System
--------------------------------------
logging_config.py file for Streamlit UI
--------------------------------------
Author: github/musicalviking
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging():
    """Configure logging based on the environment"""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Determine log level from environment or config
    from config import LOG_LEVEL

    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Determine if we should log to file (from environment)
    log_to_file = os.getenv("LOG_TO_FILE", "False").lower() == "true"
    log_file = os.getenv(
        "LOG_FILE", str(log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log')
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates on reloads
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    verbose_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Always add console handler for dev environment
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Add file handler for production environment
    if log_to_file:
        # Create a rotating file handler to manage log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=10, encoding="utf-8"  # 10MB
        )
        file_handler.setFormatter(verbose_formatter)
        root_logger.addHandler(file_handler)

    # Set specific module log levels
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    # Return the configured logger
    return logging.getLogger(__name__)


# Create a logger instance for this module
logger = setup_logging()


def get_logger(name):
    """Get a logger for a specific module"""
    return logging.getLogger(name)
