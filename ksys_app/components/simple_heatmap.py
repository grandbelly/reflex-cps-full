"""
Simple heatmap component for communication success rates
"""

import reflex as rx
from typing import List, Dict, Any


def create_heatmap_grid(state) -> rx.Component:
    """Create a simplified heatmap grid"""
    
    # Header with hour labels
    header = rx.box(
        rx.box(class_name="w-20"),  # Empty corner
        *[rx.text(str(h).zfill(2), class_name="text-xs text-center w-7") for h in range(24)],
        class_name="flex gap-0.5 mb-1"
    )
    
    # Group cells by date
    dates = []
    current_date = None
    current_row = []
    
    for cell in state.heatmap_cells:
        if cell['date'] != current_date:
            if current_row:
                dates.append((current_date, current_row))
            current_date = cell['date']
            current_row = []
        current_row.append(cell)
    
    if current_row:
        dates.append((current_date, current_row))
    
    # Create rows
    rows = []
    for date, cells in dates:
        row = rx.box(
            rx.text(date[-5:], class_name="text-xs w-20 pr-2 text-right"),
            *[
                rx.tooltip(
                    rx.box(
                        class_name=f"w-7 h-7 {cell['color']} opacity-{min(100, int(cell['value']))} hover:opacity-100 transition-opacity cursor-pointer"
                    ),
                    content=cell['label']
                )
                for cell in cells
            ],
            class_name="flex gap-0.5"
        )
        rows.append(row)
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        rx.box(
            header,
            *rows,
            class_name="overflow-x-auto"
        ),
        # Legend
        rx.box(
            rx.text("Success Rate:", class_name="text-sm font-medium mr-4"),
            rx.box(
                rx.span(class_name="inline-block w-4 h-4 bg-green-500 mr-1"),
                rx.span("≥95%", class_name="text-xs mr-3"),
                rx.span(class_name="inline-block w-4 h-4 bg-blue-500 mr-1"),
                rx.span("≥80%", class_name="text-xs mr-3"),
                rx.span(class_name="inline-block w-4 h-4 bg-amber-500 mr-1"),
                rx.span("≥60%", class_name="text-xs mr-3"),
                rx.span(class_name="inline-block w-4 h-4 bg-red-500 mr-1"),
                rx.span("<60%", class_name="text-xs"),
                class_name="flex items-center"
            ),
            class_name="flex items-center mt-4"
        ),
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )