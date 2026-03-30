"""
Recreation Inventory Management System
--------------------------------------
db_manager.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import sqlite3
import logging
import pandas as pd
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Class to manage database connections and operations"""

    @staticmethod
    def get_connection():
        """Get a connection to the SQLite database"""
        try:
            db_path = Path(__file__).parent / "inventory.db"
            return sqlite3.connect(str(db_path))
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return None

    @staticmethod
    def execute_query(query, params=(), fetch=False, commit=True):
        """Execute a SQL query with proper error handling"""
        conn = None
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return None if fetch else False

            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch:
                result = cursor.fetchall()
                if commit:
                    conn.commit()
                return result
            else:
                if commit:
                    conn.commit()
                return cursor.rowcount > 0 #Returns True only if a row was actually updated/deleted

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn and commit:
                try:
                    conn.rollback()
                except:
                    pass
            return None if fetch else False

        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    @staticmethod
    def execute_df_query(query, params=()):
        """Execute a query and return results as a pandas DataFrame"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return pd.DataFrame()

            df = pd.read_sql_query(query, conn, params=params)
            return df

        except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
            logger.error(f"Database error in execute_df_query: {e}")
            return pd.DataFrame()

        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass


def initialize_db():
    """Initialize the SQLite database with required tables"""
    from auth import hash_password
    from config import DEFAULT_ADMIN

    conn = DatabaseManager.get_connection()
    if not conn:
        return

    try:
        c = conn.cursor()

        # Create items table
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            condition TEXT DEFAULT 'Good',
            notes TEXT,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Create locations table
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Create employees table with password change requirement
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            position TEXT,
            email TEXT,
            phone TEXT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_role TEXT DEFAULT 'employee',
            is_active BOOLEAN DEFAULT 1,
            password_change_required BOOLEAN DEFAULT 0,
            password_expiry_date DATE,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Create posts table
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_username) REFERENCES employees (username)
        )
        """
        )

        # Create password history table
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS password_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            password_hash TEXT NOT NULL,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
        """
        )

        # Create default admin user if it doesn't exist
        c.execute(
            "SELECT username FROM employees WHERE username = ?",
            (DEFAULT_ADMIN["username"],),
        )
        if not c.fetchone():
            hashed_password = hash_password(DEFAULT_ADMIN["password"])
            c.execute(
                """
            INSERT INTO employees (
                first_name, last_name, position, username,
                password, user_role, password_change_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "Admin",
                    "User",
                    "System Administrator",
                    DEFAULT_ADMIN["username"],
                    hashed_password,
                    "recreation_supervisor",
                    1,
                ),
            )

        # Add default locations if they don't exist
        default_locations = [
            ("Recreation Storage", "Main recreation equipment storage area"),
            ("Gym", "Main gymnasium area"),
            ("Weight Room", "Weight training and exercise equipment area"),
            ("Office", "Recreation staff office"),
            ("Field Storage", "Outdoor equipment storage"),
            ("Equipment Room", "General equipment storage"),
        ]

        for location, description in default_locations:
            c.execute("SELECT name FROM locations WHERE name = ?", (location,))
            if not c.fetchone():
                c.execute(
                    """
                INSERT INTO locations (name, description)
                VALUES (?, ?)
                """,
                    (location, description),
                )

        # Add test items if none exist
        c.execute("SELECT COUNT(*) FROM items")
        if c.fetchone()[0] == 0:
            create_sample_items(c)

        conn.commit()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()


def create_sample_items(cursor):
    """Create sample inventory items for testing"""
    # Sample items grouped by category
    test_items = [
        # Basketball items
        (
            "Basketball",
            "Wilson Evolution Game Ball",
            "Recreation Storage",
            "Excellent",
            "Official size",
        ),
        ("Basketball", "Spalding Indoor/Outdoor Ball", "Gym", "Good", "Youth size"),
        ("Basketball", "Ball Pump", "Equipment Room", "Good", "With needle"),
        ("Basketball", "Ball Cart", "Gym", "Fair", "Holds 12 balls"),
        # Football items
        (
            "Football",
            "Wilson NFL Official Football",
            "Recreation Storage",
            "Good",
            "Game ball",
        ),
        ("Football", "Training Cones", "Field Storage", "Excellent", "Set of 20"),
        (
            "Football",
            "Flag Football Belts",
            "Equipment Room",
            "Good",
            "10 sets, red and blue",
        ),
        ("Football", "Youth Football", "Recreation Storage", "Fair", "Practice ball"),
        # Add more items as needed
    ]

    cursor.executemany(
        """
        INSERT INTO items (category, name, location, condition, notes)
        VALUES (?, ?, ?, ?, ?)
    """,
        test_items,
    )


def update_database_schema():
    """Update the database schema with new tables and columns"""
    from config import CATEGORIES, LOCATIONS

    logger.debug(f"Starting schema update with categories: {CATEGORIES}")
    logger.debug(f"Starting schema update with locations: {LOCATIONS}")

    conn = DatabaseManager.get_connection()
    if not conn:
        logger.error("Failed to get database connection for schema update")
        return False

    try:
        db_path = Path(__file__).parent / "inventory.db"
        logger.debug(f"Database path: {db_path}")
        logger.debug(f"Database exists: {db_path.exists()}")
        logger.debug(f"Database writable: {os.access(db_path, os.W_OK)}")

        c = conn.cursor()

        # Check if the is_approved column exists in employees table
        try:
            c.execute("SELECT is_approved FROM employees LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            logger.info("Adding is_approved column to employees table")
            c.execute(
                """
            ALTER TABLE employees ADD COLUMN is_approved BOOLEAN DEFAULT 0
            """
            )

            # Set existing users as approved
            c.execute(
                """
            UPDATE employees SET is_approved = 1
            """
            )

        # Update categories in the database
        try:
            # First check if categories table exists
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='categories'"
            )
            if not c.fetchone():
                # Create categories table if it doesn't exist
                logger.info("Creating categories table")
                c.execute(
                    """
                CREATE TABLE categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                )

            # Add recreation-specific categories
            for category in CATEGORIES:
                try:
                    c.execute(
                        "INSERT INTO categories (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
                        (category,),
                    )
                except sqlite3.Error as e:
                    # Handle SQLite versions that don't support ON CONFLICT DO NOTHING
                    try:
                        c.execute(
                            "INSERT INTO categories (name) VALUES (?)", (category,)
                        )
                    except sqlite3.IntegrityError:
                        # Category already exists
                        pass
        except sqlite3.Error as e:
            logger.error(f"Error updating categories: {e}")

        # Update locations in the database
        try:
            # First check if locations table exists
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='locations'"
            )
            if c.fetchone():
                # Add recreation-specific locations
                for location in LOCATIONS:
                    try:
                        c.execute(
                            "INSERT INTO locations (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
                            (location,),
                        )
                    except sqlite3.Error as e:
                        # Handle SQLite versions that don't support ON CONFLICT DO NOTHING
                        try:
                            c.execute(
                                "INSERT INTO locations (name) VALUES (?)", (location,)
                            )
                        except sqlite3.IntegrityError:
                            # Location already exists
                            pass
        except sqlite3.Error as e:
            logger.error(f"Error updating locations: {e}")

        conn.commit()
        logger.info("Database schema updated successfully")
    except sqlite3.Error as e:
        logger.error(f"Database schema update error: {e}")
        conn.rollback()
    finally:
        conn.close()
