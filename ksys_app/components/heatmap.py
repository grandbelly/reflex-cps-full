"""
Heatmap component for communication success rate visualization
"""

import reflex as rx
from typing import List, Dict, Any


def create_heatmap_cell(value: float, date: str, hour: int) -> rx.Component:
    """Create a single heatmap cell"""
    
    # Determine color based on value
    if value >= 95:
        bg_color = "bg-green-500"
        hover_color = "hover:bg-green-600"
    elif value >= 80:
        bg_color = "bg-blue-500"
        hover_color = "hover:bg-blue-600"
    elif value >= 60:
        bg_color = "bg-amber-500"
        hover_color = "hover:bg-amber-600"
    else:
        bg_color = "bg-red-500"
        hover_color = "hover:bg-red-600"
    
    opacity = f"opacity-{int(value / 10) * 10}" if value > 0 else "opacity-10"
    
    # Simple tooltip text without formatting
    tooltip_text = f"{date} Hour {hour} - {int(value)}%"
    
    return rx.el.div(
        rx.tooltip(
            rx.el.div(
                class_name=f"w-full h-full {bg_color} {opacity} {hover_color} transition-all cursor-pointer"
            ),
            content=tooltip_text
        ),
        class_name="w-8 h-8 border border-gray-200 dark:border-gray-700"
    )


def communication_heatmap(data: Dict[str, Any]) -> rx.Component:
    """
    Create a heatmap visualization for communication success rates
    
    Args:
        data: Dictionary containing:
            - dates: List of date strings
            - hours: List of hours (0-23)
            - data: Dict[date, List[success_rate]]
    """
    
    if not data or 'data' not in data:
        return rx.el.div(
            "No data available",
            class_name="text-gray-500 text-center py-8"
        )
    
    dates = data.get('dates', [])
    heatmap_data = data.get('data', {})
    
    # Create hour labels (0-23)
    hour_labels_list = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", 
                        "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
                        "20", "21", "22", "23"]
    
    hour_labels = rx.el.div(
        rx.el.div("", class_name="w-24"),  # Empty space for date labels
        rx.foreach(
            hour_labels_list,
            lambda hour: rx.el.div(
                rx.text(hour, class_name="text-xs"),
                class_name="w-8 text-center"
            )
        ),
        class_name="flex items-center mb-2"
    )
    
    # Create heatmap rows
    rows = []
    for date in dates:
        row_data = heatmap_data.get(date, [0] * 24)
        
        row = rx.el.div(
            # Date label
            rx.el.div(
                rx.text(date, class_name="text-xs"),
                class_name="w-24 pr-2 text-right"
            ),
            # Hour cells
            rx.foreach(
                list(enumerate(row_data)),
                lambda item: create_heatmap_cell(item[1], date, item[0])
            ),
            class_name="flex items-center"
        )
        rows.append(row)
    
    # Legend
    legend = rx.el.div(
        rx.el.div("Success Rate:", class_name="text-sm font-medium mr-4"),
        rx.el.div(
            rx.el.span("", class_name="inline-block w-4 h-4 bg-green-500 mr-1"),
            rx.el.span("≥95%", class_name="text-xs mr-3"),
            rx.el.span("", class_name="inline-block w-4 h-4 bg-blue-500 mr-1"),
            rx.el.span("≥80%", class_name="text-xs mr-3"),
            rx.el.span("", class_name="inline-block w-4 h-4 bg-amber-500 mr-1"),
            rx.el.span("≥60%", class_name="text-xs mr-3"),
            rx.el.span("", class_name="inline-block w-4 h-4 bg-red-500 mr-1"),
            rx.el.span("<60%", class_name="text-xs"),
            class_name="flex items-center"
        ),
        class_name="flex items-center justify-center mt-4 pt-4 border-t"
    )
    
    return rx.el.div(
        hour_labels,
        rx.el.div(
            *rows,
            class_name="space-y-0"
        ),
        legend,
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4 overflow-x-auto"
    )


def simple_heatmap(state) -> rx.Component:
    """
    Simplified heatmap using CSS Grid
    """
    
    return rx.box(
        # Title
        rx.heading(
            f"Communication Success Rate - {state.selected_tag}",
            size="5",
            class_name="mb-4"
        ),
        
        # Heatmap container
        rx.box(
            # Hour labels (top)
            rx.box(
                rx.box(class_name="w-20"),  # Empty corner
                rx.foreach(
                    list(range(24)),
                    lambda h: rx.text(
                        str(h).zfill(2),
                        class_name="text-xs text-center w-7"
                    )
                ),
                class_name="flex gap-0.5 mb-1"
            ),
            
            # Heatmap grid
            rx.foreach(
                state.heatmap_dates,
                lambda date: rx.box(
                    # Date label
                    rx.text(
                        date[-5:],  # Show only MM-DD
                        class_name="text-xs w-20 pr-2 text-right"
                    ),
                    # Hour cells for this date
                    rx.foreach(
                        list(range(24)),
                        lambda hour: rx.box(
                            class_name=rx.cond(
                                state.heatmap_data['data'][date][hour] >= 95,
                                "w-7 h-7 bg-green-500",
                                rx.cond(
                                    state.heatmap_data['data'][date][hour] >= 80,
                                    "w-7 h-7 bg-blue-500",
                                    rx.cond(
                                        state.heatmap_data['data'][date][hour] >= 60,
                                        "w-7 h-7 bg-amber-500",
                                        "w-7 h-7 bg-red-500"
                                    )
                                )
                            ),
                            style={
                                "opacity": rx.cond(
                                    state.heatmap_data['data'][date][hour] > 0,
                                    state.heatmap_data['data'][date][hour] / 100,
                                    0.1
                                )
                            },
                            title=f"{date} Hour {hour}"
                        )
                    ),
                    class_name="flex gap-0.5"
                )
            ),
            class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
        ),
        
        # Legend
        rx.box(
            rx.text("Success Rate:", class_name="font-medium mr-4"),
            rx.box(
                rx.box(class_name="w-4 h-4 bg-green-500 inline-block mr-1"),
                rx.text("≥95%", class_name="text-sm mr-4"),
                rx.box(class_name="w-4 h-4 bg-blue-500 inline-block mr-1"),
                rx.text("≥80%", class_name="text-sm mr-4"),
                rx.box(class_name="w-4 h-4 bg-amber-500 inline-block mr-1"),
                rx.text("≥60%", class_name="text-sm mr-4"),
                rx.box(class_name="w-4 h-4 bg-red-500 inline-block mr-1"),
                rx.text("<60%", class_name="text-sm"),
                class_name="flex items-center"
            ),
            class_name="flex items-center justify-center mt-4"
        ),
        class_name="w-full"
    )