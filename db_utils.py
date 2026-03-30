"""
Recreation Inventory Management System
--------------------------------------
db_utils.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import sqlite3
import time
import functools
import traceback
from contextlib import contextmanager

from logging_config import get_logger

logger = get_logger(__name__)

# Maximum number of retries for database operations
MAX_RETRIES = 3
# Delay between retries (in seconds)
RETRY_DELAY = 0.5


class DatabaseError(Exception):
    """Custom exception for database errors"""

    pass


@contextmanager
def db_transaction(connection):
    """Context manager for database transactions with error handling"""
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        logger.error(f"Database transaction failed: {str(e)}")
        logger.debug(traceback.format_exc())
        raise DatabaseError(f"Database operation failed: {str(e)}")
    finally:
        cursor.close()


def with_connection(func):
    """Decorator to provide a database connection to a function"""
    from db_manager import DatabaseManager

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = DatabaseManager.get_connection()
            return func(conn, *args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Database connection error in {func.__name__}: {str(e)}")
            raise DatabaseError(f"Database connection error: {str(e)}")
        finally:
            if conn:
                conn.close()

    return wrapper


def with_retries(func):
    """Decorator to retry database operations"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except (sqlite3.Error, DatabaseError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"Retrying database operation ({attempt+1}/{MAX_RETRIES}): {str(e)}"
                    )
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(
                        f"Database operation failed after {MAX_RETRIES} attempts: {str(e)}"
                    )

        # If we get here, all retries failed
        raise DatabaseError(
            f"Database operation failed after {MAX_RETRIES} attempts: {str(last_error)}"
        )

    return wrapper


@with_retries
@with_connection
def safe_execute(conn, query, params=None, fetch=False, fetch_one=False):
    """
    Execute a SQL query safely with error handling and retries

    Args:
        conn: Database connection
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: Whether to fetch results
        fetch_one: Whether to fetch a single row

    Returns:
        Query results if fetch is True, otherwise None
    """
    with db_transaction(conn) as cursor:
        cursor.execute(query, params or ())

        if fetch_one:
            return cursor.fetchone()
        elif fetch:
            return cursor.fetchall()
        return None


@with_retries
@with_connection
def safe_executemany(conn, query, params_list):
    """
    Execute a SQL query with multiple parameter sets

    Args:
        conn: Database connection
        query: SQL query string
        params_list: List of parameter tuples or dicts

    Returns:
        None
    """
    with db_transaction(conn) as cursor:
        cursor.executemany(query, params_list)
    return None


@with_retries
@with_connection
def safe_execute_script(conn, script):
    """
    Execute a SQL script

    Args:
        conn: Database connection
        script: SQL script string

    Returns:
        None
    """
    with db_transaction(conn) as cursor:
        cursor.executescript(script)
    return None


def check_db_health():
    """
    Check the health of the database

    Returns:
        dict: Database health information
    """
    try:
        from db_manager import DatabaseManager

        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]

        # Check foreign key constraints
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()

        # Get database size
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        size_bytes = page_count * page_size

        # Get table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        table_info = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            table_info[table] = {"row_count": row_count}

        conn.close()

        return {
            "status": (
                "healthy" if integrity == "ok" and not fk_violations else "issues"
            ),
            "integrity": integrity,
            "foreign_key_violations": len(fk_violations),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "tables": tables,
            "table_info": table_info,
        }

    except Exception as e:
        logger.error(f"Failed to check database health: {str(e)}")
        return {"status": "error", "error": str(e)}
