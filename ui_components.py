"""
Recreation Inventory Management System
--------------------------------------
ui_components.py file for Streamlit UI
--------------------------------------
Author: github/coding-with-arty
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import base64
from pathlib import Path
import io
from config import CONDITION_COLORS, CATEGORIES, LOCATIONS
import time
from db_manager import DatabaseManager
import psutil
import logging
from models import update_item, delete_item

logger = logging.getLogger(__name__)


def apply_custom_css():
    """Apply custom CSS styling to the app"""
    st.markdown(
        """
    <style>
        /* Base styles */
        :root {
            --primary-color: #1E88E5;
            --text-color: #ffffff;
            --background-color: #fff;
        }

        /* Typography */
        .stApp {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text-color);
        }

        /* Headers - responsive font sizes */
        h1 { font-size: clamp(1.5rem, 5vw, 2rem) !important; font-weight: 700 !important; text-align: center;}
        h2 { font-size: clamp(1.25rem, 4vw, 1.5rem) !important; font-weight: 600 !important; text-align: center; }
        h3 { font-size: clamp(1rem, 3vw, 1.25rem) !important; font-weight: 600 !important; text-align: center; }

        /* Cards and containers - more responsive */
        .card {
            background: var(--background-color);
            border-radius: 0.5rem;
            padding: clamp(0.5rem, 3vw, 1rem);
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            width: 100%;
            box-sizing: border-box;
            overflow-x: auto; /* Allow horizontal scrolling on small screens */
        }

        /* Stat cards */
        .stat-card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            color: white !important;
            transition: background-color 0.2s ease;
        }
        .stat-card:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            cursor: pointer;
        }
        .stat-card h2 {
            color: white !important;
            margin: 0 !important;
            font-size: 2rem !important;
            text-align: center;
        }
        .stat-card p {
            color: white !important;
            margin: 0rem 0 0 0 !important;
            opacity: 0.9;
            text-align: center;
        }

        /* Tables - responsive with horizontal scroll on mobile */
        .inventory-table {
            width: 100%;
            border-collapse: collapse;
            overflow-x: auto;
            display: block;
            max-width: 100%;
        }
        .inventory-table th {
            background: #f5f5f5;
            padding: clamp(0.3rem, 2vw, 0.5rem);
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
            white-space: nowrap;
        }
        .inventory-table td {
            border-bottom: 1px solid #eee;
            padding: clamp(0.3rem, 2vw, 0.5rem);
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Responsive tables for smaller screens */
        @media (max-width: 768px) {
            .inventory-table th,
            .inventory-table td {
                min-width: 120px;
                font-size: 14px;
            }

            /* Card-style tables for very small screens */
            .mobile-card-view .inventory-item {
                display: block;
                margin-bottom: 15px;
                padding: 10px;
                border: 1px solid #eee;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }

            .mobile-card-view .inventory-item-header {
                font-weight: bold;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
                margin-bottom: 5px;
            }

            .mobile-card-view .inventory-item-detail {
                display: flex;
                justify-content: space-between;
                padding: 2px 0;
            }

            .mobile-card-view .inventory-item-label {
                font-weight: 500;
                color: #666;
            }
        }

        /* Form elements - improved for mobile */
        input, select, textarea {
            width: 100%;
            padding: clamp(0.4rem, 2vw, 0.5rem);
            border: 1px solid #ddd;
            border-radius: 0.25rem;
            margin-bottom: 0.5rem;
            font-size: clamp(14px, 2vw, 16px);
            box-sizing: border-box;
        }

        /* Touch-friendly form elements */
        @media (max-width: 768px) {
            input, select, textarea, button {
                min-height: 44px; /* Minimum touch target size */
            }

            /* Increase spacing between form elements on mobile */
            .stForm > div {
                margin-bottom: 16px;
            }
        }

        /* Buttons with visual feedback */
        .stButton>button {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: clamp(0.4rem, 2vw, 0.5rem) clamp(0.8rem, 3vw, 1rem);
            border-radius: 0.25rem;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-width: 100px;
            font-weight: 500;
        }
        .stButton>button:hover {
            background-color: rgba(30, 136, 229, 0.9) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        .stButton>button:active {
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transform: translateY(1px);
        }

        /* Status tags */
        .condition-tag {
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
            display: inline-block;
        }

        /* Item cards */
        .item-card {
            padding: 0.75rem;
            margin: 0.25rem 0;
            border: 1px solid #eee;
            border-radius: 0.25rem;
            transition: all 0.2s ease;
        }
        .item-card:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-color: var(--primary-color);
            cursor: pointer;
        }
        .item-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.25rem;
        }
        .item-header h4 {
            margin: 0;
            font-size: 1.1rem !important;
            display: inline-block;
        }
        .item-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }
        .item-details {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-grow: 1;
        }
        .item-notes {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        .edit-form {
            padding: 0.5rem;
            background: #f8f9fa;
            border-radius: 0.25rem;
            margin-top: 0.25rem;
        }

        /* Utility classes */
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .mb-1 { margin-bottom: 0.5rem; }
        .mb-2 { margin-bottom: 1rem; }

        /* Fix for Streamlit components */
        .stSelectbox>div>div { font-size: 1rem !important; }
        .stTextInput>div>div>input { font-size: 1rem !important; }
        .stTextArea>div>div>textarea { font-size: 1rem !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Set background image for the app


def set_background(image_file):
    with open(image_file, "rb") as f:
        img_data = f.read()

    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{b64_encoded});
            background-size: cover;
        }}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)

    # Render statistics cards with item counts


def render_stats_cards(items):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f'<div class="stat-card" style="background-color: #3aa2d2;">'
            f"<h2>{len(items)}</h2>"
            f"<p>Total Items</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="stat-card" style="background-color: #3aa2d2;">'
            f'<h2>{items["category"].nunique()}</h2>'
            f"<p>Categories</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="stat-card" style="background-color: #3aa2d2;">'
            f'<h2>{items["location"].nunique()}</h2>'
            f"<p>Locations</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col4:
        conditions = items["condition"].value_counts()
        good_condition = conditions.get("Good", 0) + conditions.get("Excellent", 0)
        st.markdown(
            f'<div class="stat-card" style="background-color: #3aa2d2;">'
            f"<h2>{good_condition}</h2>"
            f"<p>Items in Good/Excellent Condition</p>"
            "</div>",
            unsafe_allow_html=True,
        )


# Render pie chart of items by category
def render_category_pie_chart(items):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Items by Category")
    categories = items["category"].value_counts()
    if not categories.empty:
        fig = px.pie(names=categories.index, values=categories.values, hole=0.4)
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=300,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Render bar chart of items by location


def render_location_bar_chart(items):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Items by Location")
    locations = items["location"].value_counts().reset_index()
    locations.columns = ["Location", "Count"]
    if not locations.empty:
        fig = px.bar(
            locations,
            x="Location",
            y="Count",
            text="Count",
            color="Count",
            color_continuous_scale="blues",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=300,
            xaxis_title="",
            yaxis_title="Number of Items",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Render item condition overview with charts


def render_condition_overview(items):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Item Conditions")
    condition_order = ["Excellent", "Good", "Fair", "Poor"]

    col1, col2 = st.columns([1, 2])

    with col1:
        # Pie chart for conditions
        condition_counts = items["condition"].value_counts()
        condition_data = pd.DataFrame(
            {
                "Condition": condition_order,
                "Count": [condition_counts.get(c, 0) for c in condition_order],
            }
        )
        fig = px.pie(
            condition_data,
            names="Condition",
            values="Count",
            color="Condition",
            color_discrete_map=CONDITION_COLORS,
        )
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20), height=250, showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Progress bars for each condition
        total_items = len(items)
        for condition in condition_order:
            count = condition_counts.get(condition, 0)
            percentage = (count / total_items * 100) if total_items > 0 else 0

            st.markdown(
                f"""
            <div style='margin-bottom: 10px;'>
                <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                    <span><b>{condition}</b></span>
                    <span>{count} items ({percentage:.1f}%)</span>
                </div>
                <div style='background-color: #f0f0f0; border-radius: 10px; height: 25px;'>
                    <div style='background-color: {CONDITION_COLORS[condition]};
                              width: {percentage}%; height: 100%;
                              border-radius: 10px; transition: width 0.5s ease;'></div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # Render a list of recently added items


def render_recent_items(items, limit=5):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Recently Added Items")
    if "created_date" in items.columns:
        recent_items = items.sort_values(by="created_date", ascending=False).head(limit)
        if not recent_items.empty:
            for _, item in recent_items.iterrows():
                st.markdown(
                    f"""
                <div style="padding: 10px; border-bottom: 1px solid #eee;">
                    <h4>{item['name']}</h4>
                    <p>Category: {item['category']} | Location: {item['location']} |
                    <span style="color: {CONDITION_COLORS[item['condition']]}">Condition: {item['condition']}</span></p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No items have been added yet.")
    else:
        st.error("'created_date' column is missing from the DataFrame.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Render the inventory items in a card layout similar to recent items


def render_inventory_table(items):
    for _, item in items.iterrows():
        # Create unique key for this item's state
        edit_key = f"edit_state_{item['id']}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        # Create columns for the item row
        cols = st.columns([5, 1, 1])

        # Display item info in the first column
        with cols[0]:
            st.markdown(
                f"""
                <div style="padding: 10px; border-bottom: 1px solid #eee;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0;">{item['name']}</h4>
                    </div>
                    <p style="margin: 5px 0;">
                        📁 {item['category']} | 📍 {item['location']} |
                        <span style="color: {CONDITION_COLORS[item['condition']]}">⚫ {item['condition']}</span>
                        {f" | 📝 {item['notes']}" if pd.notna(item['notes']) and item['notes'].strip() else ""}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Edit button in the second column
        with cols[1]:
            if st.button(
                "✏️" if not st.session_state[edit_key] else "❌",
                key=f"edit_btn_{item['id']}",
                use_container_width=True,
            ):
                st.session_state[edit_key] = not st.session_state[edit_key]
                st.rerun()

        # Delete button in the third column
        with cols[2]:
            if st.button("🗑️", key=f"delete_btn_{item['id']}", use_container_width=True):
                if st.session_state.user.get("role") == "recreation_supervisor":
                    delete_confirm_key = f"delete_confirm_{item['id']}"
                    if delete_confirm_key not in st.session_state:
                        st.session_state[delete_confirm_key] = False

                    if not st.session_state[delete_confirm_key]:
                        st.warning(f"Are you sure you want to delete '{item['name']}'?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                                "Yes, Delete",
                                key=f"confirm_delete_{item['id']}",
                                type="primary",
                            ):
                                if delete_item(item["id"]):
                                    st.success("✅ Item deleted successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete item.")
                        with col2:
                            if st.button("Cancel", key=f"cancel_delete_{item['id']}"):
                                st.session_state[delete_confirm_key] = False
                                st.rerun()
                else:
                    st.error("❌ Only supervisors can delete items.")
                    time.sleep(2)
                    st.rerun()

        # Show edit form if edit state is True
        if st.session_state[edit_key]:
            with st.form(key=f"edit_form_{item['id']}"):
                form_cols = st.columns([2, 2, 2, 1])

                # Item details
                name = form_cols[0].text_input("Name", value=item["name"])
                category = form_cols[0].selectbox(
                    "Category",
                    CATEGORIES,
                    index=(
                        CATEGORIES.index(item["category"])
                        if item["category"] in CATEGORIES
                        else 0
                    ),
                )

                location = form_cols[1].selectbox(
                    "Location",
                    LOCATIONS,
                    index=(
                        LOCATIONS.index(item["location"])
                        if item["location"] in LOCATIONS
                        else 0
                    ),
                )
                condition = form_cols[1].selectbox(
                    "Condition",
                    list(CONDITION_COLORS.keys()),
                    index=list(CONDITION_COLORS.keys()).index(item["condition"]),
                )

                notes = form_cols[2].text_input("Notes", value=item.get("notes", ""))

                if form_cols[3].form_submit_button("Save"):
                    success = update_item(
                        item["id"], category, name, location, condition, notes
                    )
                    if success:
                        st.success("✅ Updated!")
                        st.session_state[edit_key] = False
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Failed")


def render_login_form():
    """Render the login form"""
    st.markdown(
        '<h1 class="main-header">Recreation Inventory System</h1>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.header("Login")
        with st.form("login_form", clear_on_submit=False):
            login_username = st.text_input(
                "Username",
                key="login_username",
                help="Press Enter or click Login to submit",
            )
            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
                help="Press Enter or click Login to submit",
            )
            submit_login = st.form_submit_button("Login", use_container_width=True)

            return tab1, submit_login, login_username, login_password

    with tab2:
        st.header("Register")
        with st.form("register_form", clear_on_submit=True):
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input(
                "Password", type="password", key="reg_password"
            )
            submit_register = st.form_submit_button(
                "Register", use_container_width=True
            )

            return tab2, submit_register, reg_username, reg_password


# Render the sidebar navigation
def render_sidebar_navigation(user_role):
    with st.sidebar:
        # Add image at the top
        img_path = Path(__file__).parent / "3.png"
        st.image(str(img_path))
        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Recreation Department Inventory</h3>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Navigation Panel</h3>",
            unsafe_allow_html=True,
        )

        # Main navigation buttons
        if st.button("📊 Employee Dashboard", use_container_width=True):
            st.session_state.view = "dashboard"
            st.rerun()
        if st.button("📦 Department Inventory", use_container_width=True):
            st.session_state.view = "inventory"
            st.rerun()
        if st.button("➕ Add Item", use_container_width=True):
            st.session_state.view = "add"
            st.rerun()

        # Only show Admin Dashboard to recreation supervisor
        if user_role == "recreation_supervisor":
            if st.button("⚙️ Admin Dashboard", use_container_width=True):
                st.session_state.view = "admin_dashboard"
                st.rerun()

        # Add separator before user options
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        # Logout button at the bottom
        logout_clicked = st.button(
            "🚪 Logout", use_container_width=True, type="primary"
        )

        return logout_clicked

    # Render system resource statistics


def render_system_stats():
    """"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("System Resources")

    # Get CPU usage
    try:
        cpu_percent = float(psutil.cpu_percent(interval=1))
    except:
        cpu_percent = 0.0

    # Get memory usage
    try:
        memory = psutil.virtual_memory()
        memory_percent = float(memory.percent)
        memory_used = round(memory.used / (1024 * 1024 * 1024), 1)
        memory_total = round(memory.total / (1024 * 1024 * 1024), 1)
    except:
        memory_percent = 0.0
        memory_used = 0.0
        memory_total = 0.0

    # Get disk usage
    try:
        disk = psutil.disk_usage("/")
        disk_percent = float(disk.percent)
        disk_used = round(disk.used / (1024 * 1024 * 1024), 1)
        disk_total = round(disk.total / (1024 * 1024 * 1024), 1)
    except:
        disk_percent = 0.0
        disk_used = 0.0
        disk_total = 0.0

    # Create columns for stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "CPU Usage", str(cpu_percent) + "%", delta=None, delta_color="inverse"
        )

    with col2:
        st.metric(
            "Memory Usage",
            str(memory_percent) + "%",
            str(memory_used) + " GB / " + str(memory_total) + " GB",
            delta_color="inverse",
        )

    with col3:
        st.metric(
            "Disk Usage",
            str(disk_percent) + "%",
            str(disk_used) + " GB / " + str(disk_total) + " GB",
            delta_color="inverse",
        )

    # Add process information
    st.subheader("Top Processes")
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            pinfo = proc.info
            try:
                cpu_val = (
                    float(pinfo["cpu_percent"])
                    if pinfo["cpu_percent"] is not None
                    else 0.0
                )
                mem_val = (
                    float(pinfo["memory_percent"])
                    if pinfo["memory_percent"] is not None
                    else 0.0
                )
                processes.append(
                    {
                        "PID": pinfo["pid"],
                        "Name": pinfo["name"],
                        "CPU %": f"{cpu_val:.1f}",
                        "Memory %": f"{mem_val:.1f}",
                    }
                )
            except (ValueError, TypeError):
                processes.append(
                    {
                        "PID": pinfo["pid"],
                        "Name": pinfo["name"],
                        "CPU %": "0.0",
                        "Memory %": "0.0",
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort by CPU usage and get top 5
    processes.sort(key=lambda x: float(x["CPU %"]), reverse=True)
    processes = processes[:5]

    if processes:
        df = pd.DataFrame(processes)
        st.dataframe(df, hide_index=True)
    else:
        st.info("No process information available")

    st.markdown("</div>", unsafe_allow_html=True)
