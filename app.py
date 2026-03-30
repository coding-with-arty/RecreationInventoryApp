"""
Recreation Inventory Management System
--------------------------------------
Main application file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import os
import traceback
import json
from pathlib import Path
import shutil

# Force single thread mode to maintain session state
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SESSION_IDLE_TIMEOUT"] = "3600"  # 60 minutes timeout

import streamlit as st
import pandas as pd
import logging
import time
from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import tempfile
import os
from datetime import datetime
import sqlite3

# Import modules
from config import LOCATIONS, CATEGORIES, CONDITION_COLORS
from db_manager import DatabaseManager, initialize_db, update_database_schema

# Using simplified versions without external dependencies
from simple_backup import get_backup_manager
from ui_dialogs import confirm_action, show_toast, Notification
from auth import (
    authenticate_user,
    change_password,
    register_user,
    update_password_change_requirement,
    check_user_permission,
    validate_password_strength,
)
from models import (
    get_items,
    add_item,
    update_item,
    delete_item,
    get_employees,
    get_employee,
    add_employee,
    update_employee,
    add_post,
    get_posts,
    delete_post,
    get_locations,
    get_categories,
)
from pdf_generator import generate_inventory_pdf
from ui_components import (
    apply_custom_css,
    set_background,
    render_stats_cards,
    render_category_pie_chart,
    render_location_bar_chart,
    render_condition_overview,
    render_recent_items,
    render_inventory_table,
    render_login_form,
    render_sidebar_navigation,
    render_system_stats,
)

# Setup logging
from logging_config import get_logger

logger = get_logger(__name__)

# Set page config
st.set_page_config(
    page_title="Recreation Inventory",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
initialize_db()
update_database_schema()

# Apply custom CSS
apply_custom_css()

# Set background
bg_path = Path(__file__).parent / "2.png"
if bg_path.exists():
    set_background(str(bg_path))


def init_session_state():
    """Initialize all session state variables only if they don't exist"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "view" not in st.session_state:
        st.session_state.view = "login"
    if "edit_item" not in st.session_state:
        st.session_state.edit_item = None
    if "edit_employee" not in st.session_state:
        st.session_state.edit_employee = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "filter_category" not in st.session_state:
        st.session_state.filter_category = ""
    if "filter_location" not in st.session_state:
        st.session_state.filter_location = ""
    if "show_filters" not in st.session_state:
        st.session_state.show_filters = False


def force_password_change_screen():
    """Show the password change screen for users who need to change their password"""
    # Check if user is authenticated and needs password change
    if not st.session_state.get("authenticated") or not st.session_state.get("user"):
        st.session_state.view = "login"
        st.rerun()
        return

    if not st.session_state.user.get("password_change_required", False):
        # If password change is not required, redirect to appropriate view
        if st.session_state.user["role"] == "recreation_supervisor":
            st.session_state.view = "admin_dashboard"
        else:
            st.session_state.view = "dashboard"
        st.rerun()
        return

    st.title("Password Change Required")
    st.warning("You must change your password before continuing.")

    with st.form("force_password_change_form"):
        st.info("For security reasons, you need to set a new password.")

        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Change Password")

        if submit:
            if not new_password or new_password != confirm_password:
                st.error("Passwords don't match or are empty. Please try again.")
            else:
                # Check password strength
                is_valid, message = validate_password_strength(new_password)
                if not is_valid:
                    st.error(message)
                else:
                    # For admin/default user with default password
                    success, message = change_password(
                        st.session_state.user["username"],
                        (
                            "password123"
                            if st.session_state.user["username"] == "admin"
                            else None
                        ),
                        new_password,
                    )

                    if success:
                        # Password change requirement flag is already updated in the database by change_password()
                        # Just update the session state
                        st.session_state.user["password_change_required"] = False
                        st.session_state.authenticated = (
                            True  # Ensure we stay authenticated
                        )

                        # Set view based on role
                        if st.session_state.user["role"] == "recreation_supervisor":
                            st.session_state.view = "admin_dashboard"
                        else:
                            st.session_state.view = "dashboard"

                        st.success("Password changed successfully! Redirecting...")
                        st.rerun()
                    else:
                        st.error(f"Failed to change password: {message}")


def show_login_page():
    """Display the login page"""
    st.title("Recreation Inventory System")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            if username and password:
                success, message = handle_login(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please enter both username and password")


def handle_login(username, password):
    """Handle login form submission"""
    # Try to authenticate
    user_data, error_message = authenticate_user(username, password)

    if error_message:
        return False, error_message

    if not user_data:
        return False, "Invalid username or password"

    # Update session state
    st.session_state.user = user_data
    st.session_state.authenticated = True

    # Set view based on role - password change requirement is handled in main()
    if user_data.get("role") == "recreation_supervisor":
        st.session_state.view = "admin_dashboard"
    else:
        st.session_state.view = "dashboard"

    return True, "Login successful"


def dashboard_page():
    """Display the main employee dashboard"""
    st.title("Employee Dashboard")

    # Post Box Section
    st.subheader("📌 Post Box")

    # Create two columns for the post form and post display
    post_form_col, post_display_col = st.columns(2)

    # New post form in left column
    with post_form_col:
        st.subheader("New Message")
        with st.form("new_post_form"):
            post_content = st.text_area("Share a message with everyone:", height=100)
            submitted = st.form_submit_button("Post Message", use_container_width=True)
            if submitted:
                if post_content.strip():
                    if add_post(
                        st.session_state.user["username"], post_content.strip()
                    ):
                        st.success("Message posted successfully!")
                        st.rerun()
                else:
                    st.error("Please enter a message to post")

    # Display posts in right column
    with post_display_col:
        st.subheader("Recent Posts")
        posts = get_posts()
        if not posts.empty:
            # Since posts are ordered by created_date DESC, first post is latest
            for i, post in posts.iterrows():
                full_name = f"{post['first_name']} {post['last_name']}".strip()
                display_name = post["author_username"]
                if full_name and full_name != post["author_username"]:
                    display_name += f" ({full_name})"

                # Only expand the first (latest) post
                is_latest = i == 0
                with st.expander(
                    f"Posted by {display_name} on {post['created_date'][:16]}",
                    expanded=is_latest,
                ):
                    st.write(post["content"])
                    if st.session_state.user["role"] == "recreation_supervisor":
                        if st.button("Delete Post", key=f"del_post_{post['id']}"):
                            if delete_post(post["id"]):
                                st.success("Post deleted successfully!")
                                st.rerun()
        else:
            st.info("No posts yet. Be the first to post a message!")

    # Quick stats
    items = get_items()
    render_stats_cards(items)

    # Add print inventory button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(" Print Complete Inventory"):
        pdf_buffer = generate_inventory_pdf()
        st.download_button(
            label=" Download Inventory PDF",
            data=pdf_buffer,
            file_name="recreation_inventory.pdf",
            mime="application/pdf",
        )

    # Distribution Charts
    col1, col2 = st.columns(2)

    # Items by Category
    with col1:
        render_category_pie_chart(items)

    # Items by Location
    with col2:
        render_location_bar_chart(items)

    # Condition Overview
    render_condition_overview(items)

    # Recently Added Items
    render_recent_items(items)


def admin_dashboard_page():
    """Display the admin dashboard"""
    if st.session_state.user["role"] != "recreation_supervisor":
        st.error("Access denied. Only Recreation Supervisor can access this page.")
        st.session_state.view = "dashboard"
        st.rerun()

    st.title("Admin Dashboard")

    # Quick stats at the top
    items = get_items()
    render_stats_cards(items)

    # Admin tabs
    tab1, tab2, tab3 = st.tabs(
        [" System Overview", " Employee Management", " Maintenance"]
    )

    # System Overview tab
    with tab1:
        # System monitoring
        render_system_stats()

        # Post Box Section
        st.subheader("📌 Announcements")

        # Create two columns for the post form and post display
        post_form_col, post_display_col = st.columns(2)

        # New post form in left column
        with post_form_col:
            st.subheader("New Announcement")
            with st.form("new_post_form"):
                post_content = st.text_area(
                    "Share an announcement with everyone:", height=100
                )
                submitted = st.form_submit_button(
                    "Post Announcement", use_container_width=True
                )
                if submitted:
                    if post_content.strip():
                        if add_post(
                            st.session_state.user["username"], post_content.strip()
                        ):
                            st.success("Announcement posted successfully!")
                            st.rerun()
                    else:
                        st.error("Please enter an announcement to post")

        # Display posts in right column
        with post_display_col:
            st.subheader("Recent Announcements")
            posts = get_posts()
            if not posts.empty:
                for i, post in posts.iterrows():
                    full_name = f"{post['first_name']} {post['last_name']}".strip()
                    display_name = post["author_username"]
                    if full_name and full_name != post["author_username"]:
                        display_name += f" ({full_name})"

                    # Only expand the first (latest) post
                    is_latest = i == 0
                    with st.expander(
                        f"Posted by {display_name} on {post['created_date'][:16]}",
                        expanded=is_latest,
                    ):
                        st.write(post["content"])
                        if st.session_state.user["role"] == "recreation_supervisor":
                            if st.button("Delete Post", key=f"del_post_{post['id']}"):
                                if delete_post(post["id"]):
                                    st.success("Post deleted successfully!")
                                    st.rerun()
            else:
                st.info("No announcements yet. Post your first announcement!")

        # Distribution Charts
        col1, col2 = st.columns(2)

        # Items by Category
        with col1:
            render_category_pie_chart(items)

        # Items by Location
        with col2:
            render_location_bar_chart(items)

        # Condition Overview
        render_condition_overview(items)

        # Recently Added Items
        render_recent_items(items)

        # Add print inventory button
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(" Print Complete Inventory"):
            pdf_buffer = generate_inventory_pdf()
            st.download_button(
                label=" Download Inventory PDF",
                data=pdf_buffer,
                file_name="recreation_inventory.pdf",
                mime="application/pdf",
            )

    # Employee management tab
    with tab2:
        st.subheader("Employee Management")

        # Add new employee form
        with st.expander(" Add New Employee", expanded=False):
            with st.form("add_employee_form"):
                col1, col2 = st.columns(2)

                with col1:
                    first_name = st.text_input("First Name")
                    last_name = st.text_input("Last Name")
                    position = st.text_input("Position")
                    user_role = st.selectbox(
                        "Role",
                        ["employee", "recreation_supervisor"],
                        format_func=lambda x: {
                            "employee": "Employee",
                            "recreation_supervisor": "Recreation Supervisor",
                        }[x],
                    )

                with col2:
                    email = st.text_input("Email")
                    phone = st.text_input("Phone")
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")

                if st.form_submit_button("Add Employee"):
                    if all([first_name, last_name, position, username, password]):
                        success, message = add_employee(
                            first_name,
                            last_name,
                            position,
                            email,
                            phone,
                            username,
                            password,
                            user_role,
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all required fields.")

        # Pending Approvals Section
        from auth import get_pending_approvals, approve_user

        pending_approvals = get_pending_approvals()
        if pending_approvals:
            st.subheader("Pending Employee Approvals")
            st.warning(f"{len(pending_approvals)} employee(s) waiting for approval")

            for username, first_name, last_name, created_date in pending_approvals:
                with st.container():
                    cols = st.columns([2, 2, 1])
                    with cols[0]:
                        st.write(f"**{first_name} {last_name}**")
                        st.write(f"_Registered: {created_date}_")
                    with cols[1]:
                        st.write(f"Username: {username}")
                    with cols[2]:
                        if st.button("✅ Approve", key=f"approve_{username}"):
                            success, message = approve_user(
                                username, st.session_state.user
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    st.markdown("---")

        # Employee list
        st.subheader("Current Employees")
        employees = get_employees()
        if employees.empty:
            st.info("No employees found. Add your first employee using the form above.")
        else:
            for _, emp in employees.iterrows():
                with st.container():
                    cols = st.columns([2, 2, 1])
                    with cols[0]:
                        st.write(f"**{emp['first_name']} {emp['last_name']}**")
                        st.write(f"_{emp['role'].replace('_', ' ').title()}_")
                    with cols[1]:
                        st.write(f"Username: {emp['username']}")
                    with cols[2]:
                        if st.session_state.user["role"] == "recreation_supervisor":
                            if st.button("✏️ Edit", key=f"edit_{emp['username']}"):
                                st.session_state.edit_employee = emp["username"]
                                st.session_state.view = "edit_employee"
                                st.rerun()
                    st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.subheader("Database Maintenance")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Schema Operations")
            if st.button(
                "🔄 Update Database Schema",
                help="Updates table structures and default data",
            ):
                try:
                    st.info("Attempting schema update...")
                    update_database_schema()
                    st.success("Schema updated successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Schema update failed: {str(e)}")
                    with st.expander("Technical Details"):
                        st.code(
                            f"Full error:\n{traceback.format_exc()}", language="python"
                        )
                        st.write("Common fixes:")
                        st.write("- Check database file permissions")
                        st.write("- Verify config.py has valid CATEGORIES/LOCATIONS")
                        st.write("- Check logs for SQL errors")

        with col2:
            st.subheader("Backup Management")
            backup_tabs = st.tabs(["Create Backup", "Manage Backups"])

            # Create Backup Tab
            with backup_tabs[0]:
                if st.button("💾 Create New Backup", use_container_width=True):
                    try:
                        # Use our backup manager
                        backup_manager = get_backup_manager()
                        backup_path = backup_manager.create_backup()

                        if backup_path:
                            backup_file = Path(backup_path)
                            st.success(f"Backup created successfully!")
                            show_toast("Backup created", icon="✅")

                            st.download_button(
                                label="⬇️ Download Backup",
                                data=backup_file.read_bytes(),
                                file_name=backup_file.name,
                                mime="application/octet-stream",
                                use_container_width=True,
                            )
                        else:
                            st.error("Failed to create backup")
                    except Exception as e:
                        st.error(f"Backup failed: {str(e)}")
                        logger.error(f"Backup error: {str(e)}")

            # Manage Backups Tab
            with backup_tabs[1]:
                st.write("Available backups:")

                # Get available backups
                backup_manager = get_backup_manager()
                backups = backup_manager.get_available_backups()

                if not backups:
                    st.info("No backups found")
                else:
                    # Create a dataframe for display
                    backup_data = {
                        "Filename": [b["filename"] for b in backups],
                        "Date": [b["date"] for b in backups],
                        "Size": [b["size"] for b in backups],
                        "Path": [b["path"] for b in backups],
                    }
                    df = pd.DataFrame(backup_data)

                    # Display as a table
                    for i, row in df.iterrows():
                        col1, col2, col3 = st.columns([5, 2, 2])
                        with col1:
                            st.write(f"**{row['Filename']}**")
                            st.caption(f"Created: {row['Date']}")
                        with col2:
                            st.write(f"Size: {row['Size']}")
                        with col3:
                            # Restore backup button
                            if st.button("🔄 Restore", key=f"restore_{i}"):
                                # Confirm before restoring
                                if confirm_action(
                                    title="Restore Backup",
                                    message=f"Are you sure you want to restore from this backup? Current data will be overwritten.",
                                    confirm_text="Yes, Restore",
                                    dangerous=True,
                                    key_prefix=f"restore_confirm_{i}",
                                ):
                                    try:
                                        success = backup_manager.restore_backup(
                                            row["Path"]
                                        )
                                        if success:
                                            st.success(
                                                "Database restored successfully!"
                                            )
                                            show_toast("Restore completed", icon="✅")
                                            st.rerun()
                                        else:
                                            st.error("Failed to restore database")
                                    except Exception as e:
                                        st.error(f"Restore failed: {str(e)}")
                                        logger.error(f"Restore error: {str(e)}")
                        st.divider()
            if st.button("📊 Generate Health Report"):
                try:
                    pdf_buffer = generate_health_report()
                    st.success("Health report generated successfully!")
                    st.download_button(
                        label="⬇️ Download Health Report PDF",
                        data=pdf_buffer,
                        file_name=f"health_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"Report generation failed: {str(e)}")
                    with st.expander("Technical Details"):
                        st.code(
                            f"Full error:\n{traceback.format_exc()}", language="python"
                        )


def handle_delete_confirmation():
    """Handle the delete confirmation dialog and process using improved UI components"""
    if not st.session_state.delete_item_id or not st.session_state.show_delete_confirm:
        return

    # Fetch the item name for a more specific confirmation message
    items_df = get_items()
    item_data = items_df[items_df["id"] == st.session_state.delete_item_id]

    if item_data.empty:
        st.session_state.delete_item_id = None
        st.session_state.show_delete_confirm = False
        Notification.add("Item not found", type=Notification.ERROR)
        return

    item_name = item_data.iloc[0]["name"]

    # Use our improved confirmation dialog component
    confirmed = confirm_action(
        title="Delete Item",
        message=f"Are you sure you want to delete the item '{item_name}'? This action cannot be undone.",
        confirm_text="Yes, Delete",
        cancel_text="Cancel",
        icon="🗑️",
        dangerous=True,
        key_prefix=f"delete_{st.session_state.delete_item_id}",
    )

    if confirmed:
        try:
            if delete_item(st.session_state.delete_item_id):
                # Add a success notification that will show at the top of the page
                Notification.add(
                    f"Item '{item_name}' deleted successfully!",
                    type=Notification.SUCCESS,
                )
                # Also show a toast notification for immediate feedback
                show_toast(f"Item deleted successfully", icon="✅")
            else:
                Notification.add(
                    "Failed to delete item. Please try again.", type=Notification.ERROR
                )
        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            Notification.add(f"Error: {str(e)}", type=Notification.ERROR)
        finally:
            # Clear the confirmation state
            st.session_state.delete_item_id = None
            st.session_state.show_delete_confirm = False
            st.rerun()
    elif confirmed is False:  # Cancel was clicked (None means dialog is still open)
        st.session_state.delete_item_id = None
        st.session_state.show_delete_confirm = False
        st.rerun()


def inventory_page():
    """Display the inventory page"""
    st.title("Department Inventory")

    # Initialize session state for delete confirmation
    if "delete_item_id" not in st.session_state:
        st.session_state.delete_item_id = None
        st.session_state.show_delete_confirm = False

    # Handle delete confirmation first
    handle_delete_confirmation()

    # Add search box at the top
    search = st.text_input("🔍 Search items", key="search_box")

    # Add filters in a horizontal layout
    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "Filter by Category", ["All Categories"] + CATEGORIES
        )
    with col2:
        location_filter = st.selectbox(
            "Filter by Location", ["All Locations"] + LOCATIONS
        )
    with col3:
        condition_filter = st.selectbox(
            "Filter by Condition",
            ["All Conditions"]
            + ["Excellent", "Good", "Fair", "Poor", "Need for order"],
        )

    # Get all items and apply filters
    try:
        items = get_items()

        # Apply filters
        filtered_items = items.copy()
        if category_filter != "All Categories":
            filtered_items = filtered_items[
                filtered_items["category"] == category_filter
            ]
        if location_filter != "All Locations":
            filtered_items = filtered_items[
                filtered_items["location"] == location_filter
            ]
        if condition_filter != "All Conditions":
            filtered_items = filtered_items[
                filtered_items["condition"] == condition_filter
            ]

        # Apply search
        if search:
            filtered_items = filtered_items[
                filtered_items["name"].str.contains(search, case=False, na=False)
            ]

        # Display total count
        st.header(f"Total Items: {len(filtered_items)}")

        # Render inventory table
        for _, item in filtered_items.iterrows():
            with st.container():
                st.divider()
                cols = st.columns([5, 1, 1])

                # Item info
                with cols[0]:
                    st.subheader(item["name"])

                    details = [
                        f"📁 {item['category']}",
                        f"📍 {item['location']}",
                    ]

                    # Add condition with color
                    condition_color = CONDITION_COLORS[item["condition"]]
                    details.append(f"⚫ {item['condition']}")

                    if pd.notna(item["notes"]) and item["notes"].strip():
                        details.append(f"📝 {item['notes']}")

                    st.text(" | ".join(details))

                # Edit button
                with cols[1]:
                    if st.button(
                        "✏️", key=f"edit_{item['id']}", use_container_width=True
                    ):
                        st.session_state.edit_item_id = item["id"]
                        st.session_state.view = "edit"
                        st.rerun()

                # Delete button
                with cols[2]:
                    if st.button(
                        "🗑️", key=f"delete_{item['id']}", use_container_width=True
                    ):
                        if st.session_state.user.get("role") == "recreation_supervisor":
                            st.session_state.delete_item_id = item["id"]
                            st.session_state.show_delete_confirm = True
                            st.rerun()
                        else:
                            st.error("❌ Only supervisors can delete items")
                            time.sleep(1)
                            st.rerun()

        st.divider()

        # Add export buttons at the bottom
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Export to Excel"):
                # Save to Excel
                output = BytesIO()
                filtered_items.to_excel(output, index=False, engine="openpyxl")
                st.download_button(
                    label="Download Excel file",
                    data=output.getvalue(),
                    file_name="inventory.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        with col2:
            if st.button("📄 Export to PDF"):
                pdf_buffer = generate_inventory_pdf()
                st.download_button(
                    label="Download PDF file",
                    data=pdf_buffer,
                    file_name="inventory.pdf",
                    mime="application/pdf",
                )
    except Exception as e:
        st.error("Failed to load inventory items. Please try again.")
        logger.error(f"Error in inventory page: {str(e)}")
        return


def add_item_page():
    """Display the add item page"""
    st.title("Add New Item")
    st.subheader("Add a new item to the inventory")

    with st.form("add_item_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Item Name*", help="Required field")
            category = st.selectbox("Category*", CATEGORIES, help="Required field")
            location = st.selectbox("Location*", LOCATIONS, help="Required field")

        with col2:
            condition = st.selectbox(
                "Condition*",
                ["Excellent", "Good", "Fair", "Poor", "Need for order"],
                help="Required field",
            )
            notes = st.text_area("Notes (Optional)")

        submit = st.form_submit_button("Add Item")
        if submit:
            if not name:
                st.error("❌ Please enter an item name.")
            elif not category:
                st.error("❌ Please select a category.")
            elif not location:
                st.error("❌ Please select a location.")
            else:
                with st.spinner("Adding item..."):
                    if add_item(category, name, location, condition, notes):
                        st.success(f"✅ Item '{name}' added successfully!")
                        time.sleep(1)  # Give user time to see success message
                        st.session_state.view = "inventory"
                        st.rerun()
                    else:
                        st.error("❌ Failed to add item. Please try again.")

    cancel_btn = st.button("Cancel")
    if cancel_btn:
        st.session_state.view = "inventory"
        st.rerun()


def edit_item_page():
    """Display the edit item page"""
    # First check if we have an item ID but not the full item data
    if "edit_item_id" in st.session_state and st.session_state.edit_item_id is not None:
        # Fetch the item data from the database
        items_df = get_items()
        item_data = items_df[items_df["id"] == st.session_state.edit_item_id]

        if not item_data.empty:
            # Convert to dictionary
            st.session_state.edit_item = item_data.iloc[0].to_dict()
            # Clear the ID to avoid duplicate processing
            st.session_state.edit_item_id = None
        else:
            st.error("Item not found")
            st.session_state.view = "inventory"
            st.rerun()

    # Check if we have the full item data
    if "edit_item" not in st.session_state or st.session_state.edit_item is None:
        st.error("No item selected for editing")
        st.session_state.view = "inventory"
        st.rerun()

    st.title("Edit Item")
    st.subheader("Edit an existing item in the inventory")

    item_data = st.session_state.edit_item

    with st.form("edit_item_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Item Name", value=item_data["name"])

            # Category selection
            category = st.selectbox(
                "Category",
                CATEGORIES,
                index=(
                    CATEGORIES.index(item_data["category"])
                    if item_data["category"] in CATEGORIES
                    else 0
                ),
            )

            # Location selection
            location = st.selectbox(
                "Location",
                LOCATIONS,
                index=(
                    LOCATIONS.index(item_data["location"])
                    if item_data["location"] in LOCATIONS
                    else 0
                ),
            )

        with col2:
            condition = st.selectbox(
                "Condition",
                ["Excellent", "Good", "Fair", "Poor", "Need for order"],
                index=["Excellent", "Good", "Fair", "Poor", "Need for order"].index(
                    item_data["condition"]
                ),
            )
            notes = st.text_area(
                "Notes",
                value=item_data["notes"] if pd.notna(item_data["notes"]) else "",
                height=110,
            )

        col_submit, col_cancel = st.columns([1, 4])
        with col_submit:
            if st.form_submit_button("Save Changes"):
                if name and category and location:
                    if update_item(
                        item_data["id"], category, name, location, condition, notes
                    ):
                        st.success(f"Item '{name}' updated successfully!")
                        # Clear the edit item from session state
                        st.session_state.edit_item = None
                        st.session_state.view = "inventory"
                        st.rerun()
                    else:
                        st.error("Failed to update item. Please try again.")
                else:
                    st.error("Please fill in all required fields.")

        with col_cancel:
            if st.form_submit_button("Cancel"):
                # Clear the edit item from session state
                st.session_state.edit_item = None
                st.session_state.view = "inventory"
                st.rerun()


def edit_employee_page():
    """Display the edit employee page"""
    if "edit_employee" not in st.session_state or not st.session_state.edit_employee:
        st.error("No employee selected for editing")
        st.session_state.view = "admin_dashboard"
        st.rerun()

    employee = get_employee(st.session_state.edit_employee)
    if not employee:
        st.error("Employee not found")
        st.session_state.view = "admin_dashboard"
        st.rerun()

    st.title("Edit Employee")
    st.subheader("Edit an existing employee")

    with st.form("edit_employee_form"):
        col1, col2 = st.columns(2)

        with col1:
            first_name = st.text_input("First Name", value=employee["first_name"])
            last_name = st.text_input("Last Name", value=employee["last_name"])

        with col2:
            username = st.text_input(
                "Username", value=employee["username"], disabled=True
            )
            role = st.selectbox(
                "Role",
                ["employee", "recreation_supervisor"],
                index=0 if employee["role"] == "employee" else 1,
            )

        col_submit, col_cancel = st.columns([1, 4])
        with col_submit:
            if st.form_submit_button("Save Changes"):
                if first_name and last_name:
                    if update_employee(username, first_name, last_name, role):
                        st.success("Employee updated successfully!")
                        st.session_state.view = "admin_dashboard"
                        st.rerun()
                    else:
                        st.error("Failed to update employee. Please try again.")
                else:
                    st.error("Please fill in all required fields.")

        with col_cancel:
            if st.form_submit_button("Cancel"):
                st.session_state.view = "admin_dashboard"
                st.rerun()


def generate_health_report():
    """Generate a visually appealing PDF report of database health and system status"""
    # Import all required modules to ensure they're available in this function's scope
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from datetime import datetime
    from pathlib import Path
    import sqlite3

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Center alignment
    )

    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Heading2"],
        fontSize=18,
        textColor=colors.HexColor("#2196F3"),
        spaceAfter=15,
    )

    header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading3"],
        fontSize=14,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=10,
    )

    # Add report header with logo placeholder
    story.append(Paragraph("Database Health Report", title_style))
    story.append(
        Paragraph(
            f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}",
            ParagraphStyle("DateStyle", parent=styles["Normal"], alignment=1),
        )
    )
    story.append(Spacer(1, 30))

    # System Overview Section
    story.append(Paragraph("System Overview", subtitle_style))

    # Get database info
    db_path = Path(__file__).parent / "inventory.db"
    db_exists = db_path.exists()
    db_size = f"{db_path.stat().st_size/1024:.1f} KB" if db_exists else "N/A"

    # Get application info
    app_dir = Path(__file__).parent
    total_files = len(list(app_dir.glob("**/*")))
    python_files = len(list(app_dir.glob("**/*.py")))

    # System overview table
    overview_data = [
        ["Metric", "Value", "Status"],
        [
            "Database Status",
            "Connected" if db_exists else "Disconnected",
            "✓" if db_exists else "⚠",
        ],
        ["Database Size", db_size, "✓"],
        ["Last Backup", get_last_backup_date(), get_backup_status()],
        ["Environment", "Production" if is_production() else "Development", "✓"],
        ["System Files", f"{total_files} files ({python_files} Python)", "✓"],
    ]

    overview_table = Table(overview_data, colWidths=[2 * inch, 3 * inch, 1 * inch])
    overview_table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2196F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                # Content rows
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BBDEFB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),  # Center the Status column
                # Alternating row colors
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#BBDEFB")),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#BBDEFB")),
            ]
        )
    )
    story.append(overview_table)
    story.append(Spacer(1, 30))

    # Database Tables Section
    story.append(Paragraph("Database Statistics", subtitle_style))
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    # Get table statistics
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    # Table headers
    db_info = [["Table Name", "Row Count", "Last Modified", "Status"]]

    # Get statistics for each table
    for table in tables:
        table_name = table[0]
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        # Get last modified time by checking the most recent update/insert
        try:
            cursor.execute(f"SELECT MAX(last_modified) FROM {table_name}")
            last_modified = cursor.fetchone()[0]
            if not last_modified:
                last_modified = "N/A"

            # Simplified date format if it exists
            if last_modified != "N/A":
                try:
                    # Try to parse and format the date if it's in ISO format
                    parsed_date = datetime.fromisoformat(
                        last_modified.replace("Z", "+00:00")
                    )
                    last_modified = parsed_date.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    # Keep original if parsing fails
                    pass

        except sqlite3.OperationalError:
            last_modified = "N/A"

        # Determine status
        status = "✓"
        if row_count == 0:
            status = "⚠"

        db_info.append([table_name, str(row_count), str(last_modified), status])

    conn.close()

    db_table = Table(db_info, colWidths=[2 * inch, 1 * inch, 2 * inch, 1 * inch])
    db_table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2196F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                # Content formatting
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BBDEFB")),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),  # Center the count column
                ("ALIGN", (3, 1), (3, -1), "CENTER"),  # Center the status column
                # Alternating row colors for readability
            ]
            + [
                (
                    "BACKGROUND",
                    (0, i),
                    (-1, i),
                    (
                        colors.HexColor("#E3F2FD")
                        if i % 2 == 1
                        else colors.HexColor("#BBDEFB")
                    ),
                )
                for i in range(1, len(db_info))
            ]
        )
    )

    story.append(db_table)
    story.append(Spacer(1, 30))

    # Security and Configuration Analysis
    story.append(Paragraph("Security Analysis", subtitle_style))

    security_checks = [
        ["Security Check", "Status", "Recommendation"],
        [
            "Password Complexity",
            check_password_requirements(),
            "Enforce strong password requirements",
        ],
        [
            "Credential Storage",
            check_credentials_storage(),
            "Use environment variables for all credentials",
        ],
        [
            "Backup Configuration",
            get_backup_status(),
            "Verify backup paths and scheduling",
        ],
        ["Error Handling", "✓", "Continue using try/except for error resilience"],
        [
            "Production Readiness",
            check_production_readiness(),
            "Implement Docker for deployment consistency",
        ],
    ]

    security_table = Table(security_checks, colWidths=[2.5 * inch, 1 * inch, 3 * inch])
    security_table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2196F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                # Content formatting
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#BBDEFB")),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),  # Center the status column
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Color coding for status
                (
                    "TEXTCOLOR",
                    (1, 1),
                    (1, 1),
                    (
                        colors.HexColor("#4CAF50")
                        if security_checks[1][1] == "✓"
                        else colors.HexColor("#FF9800")
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (1, 2),
                    (1, 2),
                    (
                        colors.HexColor("#4CAF50")
                        if security_checks[2][1] == "✓"
                        else colors.HexColor("#FF9800")
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (1, 3),
                    (1, 3),
                    (
                        colors.HexColor("#4CAF50")
                        if security_checks[3][1] == "✓"
                        else colors.HexColor("#FF9800")
                    ),
                ),
                ("TEXTCOLOR", (1, 4), (1, 4), colors.HexColor("#4CAF50")),
                (
                    "TEXTCOLOR",
                    (1, 5),
                    (1, 5),
                    (
                        colors.HexColor("#4CAF50")
                        if security_checks[5][1] == "✓"
                        else colors.HexColor("#FF9800")
                    ),
                ),
                # Alternating row colors for readability
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#E3F2FD")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#BBDEFB")),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#BBDEFB")),
            ]
        )
    )

    story.append(security_table)
    story.append(Spacer(1, 30))

    # Recommendations section
    story.append(Paragraph("Recommendations", subtitle_style))

    recommendations = [
        "1. Replace hardcoded credentials with environment variables in all scripts",
        "2. Complete implementation of password complexity requirements for all users",
        "3. Finalize Docker configuration for production deployment",
        "4. Set up comprehensive logging for all application activities",
        "5. Verify all configuration paths for production environment",
        "6. Regularly test database backup and recovery procedures",
    ]

    for rec in recommendations:
        story.append(
            Paragraph(
                rec,
                ParagraphStyle(
                    "Recommendation",
                    parent=styles["Normal"],
                    leftIndent=20,
                    spaceAfter=6,
                ),
            )
        )

    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def check_password_requirements():
    """Check if password complexity requirements are implemented"""
    # Check for password validation function - safer approach without dynamic imports
    try:
        # Check if the auth module has the validate_password_strength function
        import auth

        if hasattr(auth, "validate_password_strength"):
            # If function exists, return check mark
            return "✓"
        return "⚠"
    except Exception:
        return "⚠"


def check_credentials_storage():
    """Check if credentials are properly stored in environment variables"""
    # This would normally do a more thorough check
    # For this report, we'll just show a warning as a placeholder
    return "⚠"


def get_last_backup_date():
    """Get the date of the last database backup"""
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        return "No backups found"

    backup_files = list(backup_dir.glob("inventory_backup_*.db"))
    if not backup_files:
        return "No backups found"

    # Get the most recent backup file
    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
    backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
    return backup_time.strftime("%Y-%m-%d %H:%M")


def get_backup_status():
    """Check backup status"""
    backup_dir = Path(__file__).parent / "backups"
    if not backup_dir.exists():
        return "⚠"

    backup_files = list(backup_dir.glob("inventory_backup_*.db"))
    if not backup_files:
        return "⚠"

    # Check if the most recent backup is within the last 7 days
    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
    backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
    days_since_backup = (datetime.now() - backup_time).days

    return "✓" if days_since_backup < 7 else "⚠"


def is_production():
    """Determine if running in production environment"""
    # This is a placeholder function - in a real app this would check
    # environment variables or other deployment indicators
    return False


def check_production_readiness():
    """Check if the app is ready for production"""
    # Check for Docker configuration
    docker_file = Path(__file__).parent / "Dockerfile"
    if docker_file.exists():
        return "✓"
    return "⚠"


def clean_old_backups():
    """Clean up old database backups, keeping the 10 most recent"""
    try:
        backup_dir = Path(__file__).parent / "backups"
        if not backup_dir.exists():
            return

        backup_files = list(backup_dir.glob("inventory_backup_*.db"))
        if len(backup_files) <= 10:
            return

        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Delete all but the 10 most recent backups
        for old_backup in backup_files[10:]:
            old_backup.unlink()
    except Exception as e:
        logger.error(f"Error cleaning old backups: {str(e)}")
        # Don't raise the exception - this is a maintenance task that shouldn't stop the app
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        if integrity_result == "ok":
            health_info.append(["✓ Data Integrity", "Database passed integrity check"])
        else:
            health_info.append(["⚠ Data Integrity", "Database failed integrity check"])
        cursor.close()
    except Exception as e:
        health_info.append(["⚠ Data Integrity", f"Could not verify: {str(e)}"])

    health_table = Table(health_info, colWidths=[2 * inch, 4 * inch])
    health_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(health_table)

    # Build the PDF
    doc.build(story)
    return pdf_path


def clean_old_backups():
    backup_dir = Path(__file__).parent / "backups"
    if backup_dir.exists():
        backups = [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == ".db"]
        backups.sort(key=lambda f: f.stat().st_ctime)
        for backup in backups[:-5]:  # Keep the last 5 backups
            backup.unlink()


def main():
    """Main application entry point"""
    try:
        # Initialize session state variables
        init_session_state()

        # Check if backup is needed (once per day)
        backup_manager = get_backup_manager()
        if backup_manager.should_backup(hours=24):
            try:
                backup_path = backup_manager.create_backup()
                if backup_path:
                    logger.info(f"Automatic backup created: {backup_path}")
            except Exception as e:
                logger.error(f"Automatic backup failed: {str(e)}")

        # Display any pending notifications at the top of the app
        Notification.show()

        if not st.session_state.authenticated:
            show_login_page()
        else:
            # Render sidebar navigation first
            logout_clicked = render_sidebar_navigation(
                st.session_state.user.get("role", "employee")
            )

            if logout_clicked:
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                init_session_state()
                st.rerun()
                return

            if st.session_state.user.get("password_change_required", False):
                force_password_change_screen()
            else:
                # Show appropriate view based on current state
                if st.session_state.view == "dashboard":
                    dashboard_page()
                elif st.session_state.view == "inventory":
                    inventory_page()
                elif st.session_state.view == "add":
                    add_item_page()
                elif st.session_state.view == "edit":
                    edit_item_page()
                elif st.session_state.view == "admin_dashboard":
                    if st.session_state.user.get("role") == "recreation_supervisor":
                        admin_dashboard_page()
                    else:
                        st.session_state.view = "dashboard"
                        st.rerun()
                elif st.session_state.view == "edit_employee":
                    if st.session_state.user.get("role") == "recreation_supervisor":
                        edit_employee_page()
                    else:
                        st.session_state.view = "dashboard"
                        st.rerun()
                else:
                    # Default to dashboard for invalid views
                    st.session_state.view = "dashboard"
                    st.rerun()

    except Exception as e:
        print(f"Error in main: {str(e)}")
        st.error("An error occurred. Please try again.")


if __name__ == "__main__":
    main()
