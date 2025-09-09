"""
Grid Heatmap using CSS Grid - Reflex compatible
"""

import reflex as rx
from typing import List, Dict, Any


def create_cell(value: float, date: str, hour: int) -> rx.Component:
    """Create a single heatmap cell"""
    
    # Color based on value
    color_class = rx.cond(
        value >= 95,
        "bg-green-500 hover:bg-green-600",
        rx.cond(
            value >= 80,
            "bg-blue-500 hover:bg-blue-600",
            rx.cond(
                value >= 60,
                "bg-amber-400 hover:bg-amber-500",
                "bg-red-500 hover:bg-red-600"
            )
        )
    )
    
    # Opacity based on value (0-100 mapped to 0.3-1.0)
    opacity = max(0.3, min(1.0, value / 100))
    
    return rx.box(
        rx.tooltip(
            rx.box(
                rx.text(
                    f"{int(value)}",
                    class_name="text-xs text-white font-medium"
                ),
                class_name=f"{color_class} w-full h-8 flex items-center justify-center cursor-pointer transition-all",
                style={"opacity": opacity}
            ),
            content=f"{date} {hour:02d}:00 - {value:.1f}%"
        ),
        class_name="border border-gray-200 dark:border-gray-700"
    )


def css_grid_heatmap(state) -> rx.Component:
    """
    Create a CSS Grid based heatmap that works well with Reflex
    """
    
    # Create flat list of cells with grid positions
    cells = []
    for row_idx, date in enumerate(state.date_labels):
        for col_idx in range(24):
            if state.heatmap_matrix and row_idx < len(state.heatmap_matrix):
                value = state.heatmap_matrix[row_idx][col_idx] if col_idx < len(state.heatmap_matrix[row_idx]) else 0
            else:
                value = 0
            
            cells.append({
                "date": date,
                "hour": col_idx,
                "value": value,
                "row": row_idx + 2,  # +2 for header row
                "col": col_idx + 2   # +2 for label column
            })
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Grid Container
        rx.box(
            # Corner cell
            rx.box(class_name="col-start-1 row-start-1"),
            
            # Hour labels (top)
            *[
                rx.text(
                    f"{h:02d}",
                    class_name=f"col-start-{h+2} row-start-1 text-xs text-center",
                    style={"grid-column": h+2, "grid-row": 1}
                )
                for h in range(24)
            ],
            
            # Date labels (left) and cells
            *[
                rx.box(
                    rx.text(
                        date[-5:],  # Show MM-DD only
                        class_name="text-xs pr-2 text-right"
                    ),
                    style={"grid-column": 1, "grid-row": idx+2},
                    class_name="flex items-center"
                )
                for idx, date in enumerate(state.date_labels)
            ],
            
            # Data cells
            *[
                rx.box(
                    create_cell(cell["value"], cell["date"], cell["hour"]),
                    style={"grid-column": cell["col"], "grid-row": cell["row"]}
                )
                for cell in cells
            ],
            
            class_name="grid gap-0.5",
            style={
                "display": "grid",
                "grid-template-columns": "80px " + " ".join(["32px"] * 24),
                "grid-template-rows": "20px " + " ".join(["32px"] * len(state.date_labels))
            }
        ),
        
        # Legend
        rx.box(
            rx.text("Success Rate:", class_name="text-sm font-medium mr-4"),
            rx.box(
                rx.box(class_name="inline-block w-4 h-4 bg-green-500 mr-1"),
                rx.text("≥95%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-blue-500 mr-1"),
                rx.text("≥80%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-amber-400 mr-1"),
                rx.text("≥60%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-red-500 mr-1"),
                rx.text("<60%", class_name="text-xs"),
                class_name="flex items-center"
            ),
            class_name="flex items-center mt-4"
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4 overflow-x-auto"
    )