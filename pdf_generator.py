"""
Recreation Inventory Management System
--------------------------------------
pdf_generator.py file for Streamlit UI
--------------------------------------
Author: github/musicalviking
"""

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
import pandas as pd

from models import get_items, get_locations
from config import CONDITION_COLORS


def generate_inventory_pdf():
    """Generate a PDF report of the complete inventory with charts"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Create custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
    )

    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Heading2"],
        fontSize=18,
        textColor=colors.HexColor("#2196F3"),
        spaceAfter=20,
    )

    # Add title and date
    elements.append(Paragraph("Recreation Department Inventory", title_style))
    elements.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')}", styles["Normal"]
        )
    )
    elements.append(Spacer(1, 20))

    # Get inventory data
    items = get_items()

    # Add summary statistics
    elements.append(Paragraph("Summary Statistics", subtitle_style))

    # Create summary table
    summary_data = [
        ["Total Items", "Total Categories", "Total Locations"],
        [
            str(len(items)),
            str(items["category"].nunique()),
            str(items["location"].nunique()),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[2 * inch] * 3)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2196F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Create condition distribution section
    create_condition_section(elements, items, subtitle_style)

    # Create location inventory sections
    create_location_sections(elements, items, styles)

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def create_condition_section(elements, items, subtitle_style):
    """Create the condition distribution section of the PDF"""
    elements.append(Paragraph("Items by Condition", subtitle_style))
    condition_counts = items["condition"].value_counts()
    condition_colors = {
        "Excellent": colors.HexColor("#4CAF50"),
        "Good": colors.HexColor("#2196F3"),
        "Fair": colors.HexColor("#FFC107"),
        "Poor": colors.HexColor("#F44336"),
    }

    condition_data = [["Condition", "Count"]]
    for condition, count in condition_counts.items():
        condition_data.append([condition, str(count)])

    condition_table = Table(condition_data, colWidths=[3 * inch, 3 * inch])
    condition_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
            + [
                (
                    "BACKGROUND",
                    (0, i),
                    (-1, i),
                    (
                        colors.HexColor("#FFFFFF")
                        if i % 2 == 0
                        else colors.HexColor("#F5F5F5")
                    ),
                )
                for i in range(1, len(condition_data))
            ]
            + [
                (
                    "TEXTCOLOR",
                    (0, i),
                    (0, i),
                    condition_colors.get(row[0], colors.black),
                )
                for i, row in enumerate(condition_data[1:], 1)
            ]
        )
    )
    elements.append(condition_table)
    elements.append(Spacer(1, 30))


def create_location_sections(elements, items, styles):
    """Create inventory by location sections in the PDF"""
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Heading2"],
        fontSize=18,
        textColor=colors.HexColor("#2196F3"),
        spaceAfter=20,
    )

    elements.append(Paragraph("Inventory by Location", subtitle_style))
    locations = get_locations()
    condition_colors = {
        "Excellent": colors.HexColor("#4CAF50"),
        "Good": colors.HexColor("#2196F3"),
        "Fair": colors.HexColor("#FFC107"),
        "Poor": colors.HexColor("#F44336"),
    }

    for location in sorted(locations):
        # Location header with item count
        location_items = items[items["location"] == location]
        total_items = len(location_items)

        elements.append(
            Paragraph(
                f"{location} ({total_items} items)",
                ParagraphStyle(
                    "LocationHeader",
                    parent=styles["Heading3"],
                    textColor=colors.HexColor("#1976D2"),
                ),
            )
        )
        elements.append(Spacer(1, 10))

        if len(location_items) > 0:
            # Create table for this location
            table_data = [["Item Name", "Category", "Condition", "Notes"]]
            for _, item in location_items.iterrows():
                table_data.append(
                    [
                        item["name"],
                        item["category"],
                        item["condition"],
                        item["notes"] if pd.notna(item["notes"]) else "",
                    ]
                )

            table = Table(
                table_data, colWidths=[2 * inch, 1.5 * inch, 1 * inch, 2.5 * inch]
            )
            table.setStyle(
                TableStyle(
                    [
                        # Header style
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        # Content style
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("ROWHEIGHT", (0, 0), (-1, -1), 30),
                    ]
                    + [
                        # Alternating row colors
                        (
                            "BACKGROUND",
                            (0, i),
                            (-1, i),
                            (
                                colors.HexColor("#FFFFFF")
                                if i % 2 == 0
                                else colors.HexColor("#F5F5F5")
                            ),
                        )
                        for i in range(1, len(table_data))
                    ]
                    + [
                        # Condition color coding
                        (
                            "TEXTCOLOR",
                            (2, i),
                            (2, i),
                            condition_colors.get(row[2], colors.black),
                        )
                        for i, row in enumerate(table_data[1:], 1)
                    ]
                )
            )
            elements.append(table)
        else:
            elements.append(Paragraph("No items in this location", styles["Italic"]))

        elements.append(Spacer(1, 20))
