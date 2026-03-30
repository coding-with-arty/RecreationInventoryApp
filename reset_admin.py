"""
Recreation Inventory Management System
--------------------------------------
reset_admin.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

from pathlib import Path
import os
import random
import string
from db_manager import DatabaseManager
from auth import hash_password


def reset_admin_password():
    """Reset admin password and ensure it's using the correct database"""
    print("\n=== Admin Password Reset ===")

    # Get current password hash for reference
    query = "SELECT password FROM employees WHERE username = 'admin'"
    result = DatabaseManager.execute_query(query, fetch=True)

    if result and result[0]:
        current_hash = result[0][0]
        print(f"Current password hash: {current_hash}")
    else:
        print("Admin user not found!")
        return

    # Hash the default password
    default_password = "password123"
    hashed_password = hash_password(default_password)
    print(f"New password hash: {hashed_password}")

    # Reset admin password and require password change
    update_query = """
        UPDATE employees
        SET password = ?, password_change_required = 1
        WHERE username = 'admin'
    """
    DatabaseManager.execute_query(update_query, (hashed_password,))

    # Verify the change
    verify_query = "SELECT password, password_change_required FROM employees WHERE username = 'admin'"
    result = DatabaseManager.execute_query(verify_query, fetch=True)

    if result and result[0]:
        print("\nReset successful!")
        print(f"New stored hash: {result[0][0]}")
        print(f"Password change required: {'Yes' if result[0][1] else 'No'}")
        print("\nAdmin password has been reset to the temporary password")
        print("You can now log in with:")
        print("Username: admin")
        print(f"Password: {default_password}")
    else:
        print("Error: Could not verify the password update!")


if __name__ == "__main__":
    reset_admin_password()
