"""
Recreation Inventory Management System
--------------------------------------
Auth.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import hashlib
import datetime
from db_manager import DatabaseManager

# Track failed login attempts
_login_attempts = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    return hash_password(password) == hashed_password


def validate_password_strength(password):
    """Check if password meets minimum security requirements"""
    from config import MIN_PASSWORD_LENGTH

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"

    # Check for at least one uppercase, one lowercase, and one digit
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        return (
            False,
            "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character",
        )

    return True, "Password meets requirements"


def check_rate_limit(username):
    """Check if a user has exceeded login attempts"""
    now = datetime.datetime.now()
    if username in _login_attempts:
        attempts, lockout_until = _login_attempts[username]
        if lockout_until and now < lockout_until:
            return (
                False,
                f"Account locked. Try again in {int((lockout_until - now).total_seconds() / 60)} minutes",
            )
        if now >= lockout_until:
            _login_attempts[username] = (0, None)
    return True, None


def update_login_attempts(username, success):
    """Update login attempts for rate limiting"""
    now = datetime.datetime.now()
    if success:
        if username in _login_attempts:
            del _login_attempts[username]
    else:
        attempts, _ = _login_attempts.get(username, (0, None))
        attempts += 1
        lockout_until = (
            now + datetime.timedelta(minutes=_LOCKOUT_MINUTES)
            if attempts >= _MAX_ATTEMPTS
            else None
        )
        _login_attempts[username] = (attempts, lockout_until)


def authenticate_user(username, password):
    """Authenticate user and return user information"""
    # Check rate limiting
    can_attempt, error_msg = check_rate_limit(username)
    if not can_attempt:
        return None, error_msg

    # Get user information in a single query
    query = """
        SELECT username, first_name, last_name, user_role, password_change_required, id, password, is_approved
        FROM employees
        WHERE username = ?
    """
    result = DatabaseManager.execute_query(query, (username,), fetch=True)

    if not result or not result[0]:
        update_login_attempts(username, False)
        return None, "Invalid username or password"

    user = result[0]
    stored_hash = user[6]
    is_approved = user[7]

    # Check if user is approved
    if not is_approved:
        return None, "Your account is pending admin approval"

    # Verify password
    if not verify_password(password, stored_hash):
        update_login_attempts(username, False)
        return None, "Invalid username or password"

    # Authentication successful
    update_login_attempts(username, True)
    return {
        "username": user[0],
        "first_name": user[1],
        "last_name": user[2],
        "role": user[3],
        "password_change_required": bool(user[4]),
        "id": user[5],
    }, None


def change_password(username, old_password, new_password):
    """Change a user's password"""
    # If old_password is None, skip verification (used for password reset)
    if old_password is not None:
        # Verify old password first
        auth_result = authenticate_user(username, old_password)
        if not auth_result[0]:  # Check first element of tuple
            return False, "Current password is incorrect"

    # Hash and store new password
    hashed_password = hash_password(new_password)

    # Update password in database and set password_change_required to False
    query = """
        UPDATE employees
        SET password = ?, password_change_required = 0
        WHERE username = ?
    """
    DatabaseManager.execute_query(query, (hashed_password, username))

    # Verify the change
    verify_query = "SELECT password FROM employees WHERE username = ? AND password = ?"
    result = DatabaseManager.execute_query(
        verify_query, (username, hashed_password), fetch=True
    )

    if result and result[0]:
        return True, "Password changed successfully"
    return False, "Failed to update password"


def update_password_change_requirement(username, required=False, admin_user=None):
    """Update whether a user needs to change their password.
    Admin privileges are required to set this flag for other users,
    but users can update their own flag when changing passwords."""
    # Skip admin check if user is updating their own password change requirement to False
    # This allows users to clear their own flag after changing password
    user_updating_own_flag = admin_user is None and required is False

    # For all other cases (setting flag to True or changing another user's flag), require admin
    if not user_updating_own_flag and (
        not admin_user or not check_user_permission(admin_user, "admin")
    ):
        return False, "Only administrators can set password change requirements"

    query = """
        UPDATE employees
        SET password_change_required = ?
        WHERE username = ?
    """
    DatabaseManager.execute_query(query, (1 if required else 0, username))

    # Verify the change
    verify_query = "SELECT password_change_required FROM employees WHERE username = ?"
    result = DatabaseManager.execute_query(verify_query, (username,), fetch=True)

    if result and result[0] and result[0][0] == (1 if required else 0):
        return True, "Password change requirement updated successfully"
    return False, "Failed to update password change requirement"


def is_password_in_history(employee_id, new_password, history_limit=5):
    """Check if password was used recently by this employee"""
    query = """
        SELECT password_hash FROM password_history
        WHERE employee_id = ?
        ORDER BY created_date DESC
        LIMIT ?
    """
    result = DatabaseManager.execute_query(
        query, (employee_id, history_limit), fetch=True
    )

    if not result:
        return False

    new_hash = hash_password(new_password)
    return any(new_hash == row[0] for row in result)


def check_user_permission(user, required_role):
    """Check if the user has the required role or higher"""
    if not user or isinstance(user, tuple):
        return False

    from config import ROLE_HIERARCHY

    user_role = user.get("role", "employee")
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    user_level = ROLE_HIERARCHY.get(user_role, 0)

    return user_level >= required_level


def authorize_user(username, user_role):
    """Authorize a user and set their role"""
    query = """
        UPDATE employees
        SET user_role = ?
        WHERE username = ?
    """
    DatabaseManager.execute_query(query, (user_role, username))
    return True


def register_user(username, password, first_name="", last_name=""):
    """Register a new user (requires admin approval)"""
    # Check if username already exists
    check_query = "SELECT username FROM employees WHERE username = ?"
    result = DatabaseManager.execute_query(check_query, (username,), fetch=True)

    if result and result[0]:
        return False, "Username already exists. Please choose a different username."

    # Validate password strength
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        return False, message

    # Insert new employee with default role, no password change required, and pending approval
    insert_query = """
        INSERT INTO employees (
            username, password, first_name, last_name,
            user_role, password_change_required, is_approved
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    hashed_password = hash_password(password)
    DatabaseManager.execute_query(
        insert_query,
        (username, hashed_password, first_name, last_name, "employee", 0, 0),
    )

    # Verify the registration
    verify_query = "SELECT username FROM employees WHERE username = ?"
    result = DatabaseManager.execute_query(verify_query, (username,), fetch=True)

    if result and result[0]:
        return True, "Registration successful! Please wait for admin approval to login."
    return False, "Failed to register user"


def approve_user(username, admin_user=None):
    """Approve a user registration (admin only)"""
    # Check if the requesting user is an admin or recreation supervisor
    if not admin_user or not (
        check_user_permission(admin_user, "admin")
        or admin_user.get("role") == "recreation_supervisor"
    ):
        return False, "Only administrators can approve user registrations"

    # Update user approval status
    query = """
        UPDATE employees
        SET is_approved = 1
        WHERE username = ?
    """
    DatabaseManager.execute_query(query, (username,))

    # Verify the approval
    verify_query = "SELECT is_approved FROM employees WHERE username = ?"
    result = DatabaseManager.execute_query(verify_query, (username,), fetch=True)

    if result and result[0] and result[0][0] == 1:
        return True, f"User {username} has been approved"
    return False, f"Failed to approve user {username}"


def get_pending_approvals():
    """Get list of users pending approval (admin only)"""
    query = """
        SELECT username, first_name, last_name, created_date
        FROM employees
        WHERE is_approved = 0
        ORDER BY created_date DESC
    """
    result = DatabaseManager.execute_query(query, fetch=True)

    if result:
        return [(row[0], row[1], row[2], row[3]) for row in result]
    return []
