"""
Recreation Inventory Management System
--------------------------------------
reset_password.py file for Streamlit UI
--------------------------------------
Author: github/musicalviking
"""

from pathlib import Path
from db_manager import DatabaseManager
from auth import hash_password


def reset_password(username="admin", new_password="password123"):
    """Reset a user's password and require password change"""
    print(f"\n=== Resetting Password for {username} ===")

    # Hash the new password
    hashed_password = hash_password(new_password)
    print(f"New password hash: {hashed_password}")

    # Update the password in the database
    update_query = """
        UPDATE employees
        SET password = ?, password_change_required = 1
        WHERE username = ?
    """
    DatabaseManager.execute_query(update_query, (hashed_password, username))

    # Verify the change
    verify_query = (
        "SELECT password, password_change_required FROM employees WHERE username = ?"
    )
    result = DatabaseManager.execute_query(verify_query, (username,), fetch=True)

    if result and result[0]:
        print("\nPassword reset successful!")
        print(f"New stored hash: {result[0][0]}")
        print(f"Password change required: {'Yes' if result[0][1] else 'No'}")
        print(f"\nUser can now log in with:")
        print(f"Username: {username}")
        print(f"Password: {new_password}")
    else:
        print(f"Error: Could not verify password update for user: {username}")


if __name__ == "__main__":
    reset_password()
