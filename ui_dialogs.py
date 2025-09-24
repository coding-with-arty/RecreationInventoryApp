"""
Recreation Inventory Management System
--------------------------------------
ui_dialogs.py file for Streamlit UI
--------------------------------------
Author: github/musicalviking
"""

import streamlit as st
import time
from logging_config import get_logger

logger = get_logger(__name__)


def confirm_action(
    title,
    message,
    confirm_text="Confirm",
    cancel_text="Cancel",
    icon="⚠️",
    dangerous=False,
    key_prefix="confirm",
):
    """
    Display a confirmation dialog and return the user's choice

    Args:
        title: Dialog title
        message: Dialog message
        confirm_text: Text for the confirm button
        cancel_text: Text for the cancel button
        icon: Icon to display
        dangerous: Whether this is a dangerous action (red confirm button)
        key_prefix: Prefix for session state keys

    Returns:
        bool: True if confirmed, False otherwise
    """
    unique_key = f"{key_prefix}_{hash(title + message)}"
    confirmed_key = f"{unique_key}_confirmed"
    canceled_key = f"{unique_key}_canceled"
    dialog_key = f"{unique_key}_dialog"

    # Initialize session state if needed
    if dialog_key not in st.session_state:
        st.session_state[dialog_key] = False
        st.session_state[confirmed_key] = False
        st.session_state[canceled_key] = False

    # If dialog is not open and we haven't decided yet, show the dialog
    if (
        not st.session_state[dialog_key]
        and not st.session_state[confirmed_key]
        and not st.session_state[canceled_key]
    ):
        st.session_state[dialog_key] = True

    # If dialog is open, show it
    if st.session_state[dialog_key]:
        with st.container():
            st.markdown(
                f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #{'dc3545' if dangerous else '17a2b8'};'>",
                unsafe_allow_html=True,
            )
            st.markdown(f"### {icon} {title}")
            st.write(message)

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    confirm_text,
                    key=f"{unique_key}_confirm_btn",
                    type="primary" if not dangerous else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[confirmed_key] = True
                    st.session_state[dialog_key] = False
                    logger.info(f"Action confirmed: {title}")
                    return True

            with col2:
                if st.button(
                    cancel_text,
                    key=f"{unique_key}_cancel_btn",
                    type="secondary" if not dangerous else "primary",
                    use_container_width=True,
                ):
                    st.session_state[canceled_key] = True
                    st.session_state[dialog_key] = False
                    logger.info(f"Action canceled: {title}")
                    return False

            st.markdown("</div>", unsafe_allow_html=True)

    # Return the decision if already made
    return st.session_state[confirmed_key]


def show_toast(message, icon="ℹ️", duration=3):
    """
    Display a toast notification

    Args:
        message: Toast message
        icon: Icon to display
        duration: Duration in seconds
    """
    try:
        st.toast(f"{icon} {message}", icon=None)
    except Exception:
        # Older versions of Streamlit don't support toast
        st.info(f"{icon} {message}")
        time.sleep(duration)
        st.rerun()


class Notification:
    """Class for managing notifications in the app"""

    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"

    @staticmethod
    def clear():
        """Clear all notifications"""
        if "notifications" in st.session_state:
            del st.session_state.notifications

    @staticmethod
    def has_notifications():
        """Check if there are any notifications"""
        return (
            hasattr(st.session_state, "notifications")
            and st.session_state.notifications
        )

    @staticmethod
    def add(message, type=INFO, dismissable=True, duration=None):
        """
        Add a notification to be displayed

        Args:
            message: Notification message
            type: Notification type (error, success, info, warning)
            dismissable: Whether the notification can be dismissed
            duration: Auto-dismiss duration in seconds (None for no auto-dismiss)
        """
        if not hasattr(st.session_state, "notifications"):
            st.session_state.notifications = []

        notification_id = hash(f"{message}_{type}_{time.time()}")

        st.session_state.notifications.append(
            {
                "id": notification_id,
                "message": message,
                "type": type,
                "dismissable": dismissable,
                "duration": duration,
                "created_at": time.time(),
            }
        )

        logger.info(f"Added notification ({type}): {message}")

    @staticmethod
    def dismiss(notification_id):
        """Dismiss a notification by ID"""
        if hasattr(st.session_state, "notifications"):
            st.session_state.notifications = [
                n for n in st.session_state.notifications if n["id"] != notification_id
            ]

    @staticmethod
    def show():
        """Display all current notifications"""
        if not hasattr(st.session_state, "notifications"):
            return

        current_time = time.time()
        notifications_to_keep = []

        for notification in st.session_state.notifications:
            # Check if notification should be auto-dismissed
            if notification["duration"] is not None:
                if current_time - notification["created_at"] > notification["duration"]:
                    continue  # Skip this notification

            # Display the notification
            with st.container():
                type_colors = {
                    Notification.ERROR: "#dc3545",  # Red
                    Notification.SUCCESS: "#28a745",  # Green
                    Notification.INFO: "#17a2b8",  # Blue
                    Notification.WARNING: "#ffc107",  # Yellow
                }

                type_icons = {
                    Notification.ERROR: "❌",
                    Notification.SUCCESS: "✅",
                    Notification.INFO: "ℹ️",
                    Notification.WARNING: "⚠️",
                }

                color = type_colors.get(
                    notification["type"], type_colors[Notification.INFO]
                )
                icon = type_icons.get(
                    notification["type"], type_icons[Notification.INFO]
                )

                cols = (
                    st.columns([10, 1])
                    if notification["dismissable"]
                    else [st.container()]
                )

                with cols[0]:
                    st.markdown(
                        f"<div style='background-color: {color}22; color: {color}; padding: 10px; "
                        f"border-radius: 5px; border-left: 5px solid {color};'>"
                        f"{icon} {notification['message']}</div>",
                        unsafe_allow_html=True,
                    )

                if notification["dismissable"]:
                    with cols[1]:
                        if st.button(
                            "✕",
                            key=f"dismiss_{notification['id']}",
                            help="Dismiss this notification",
                        ):
                            Notification.dismiss(notification["id"])
                            st.rerun()

            notifications_to_keep.append(notification)

        # Update the list to only keep non-expired notifications
        st.session_state.notifications = notifications_to_keep
