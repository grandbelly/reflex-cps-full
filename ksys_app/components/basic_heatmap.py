"""
Basic heatmap component - minimal version
"""

import reflex as rx


def basic_heatmap(state) -> rx.Component:
    """Create a basic heatmap visualization"""
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Show tag and period
        rx.box(
            rx.text(f"Tag: {state.selected_tag}", class_name="text-sm"),
            rx.text(f"Period: Last {state.selected_days} days", class_name="text-sm"),
            class_name="mb-4 text-gray-600 dark:text-gray-400"
        ),
        
        # Simple data display
        rx.cond(
            state.heatmap_dates,
            rx.box(
                rx.text("Hourly Success Rates by Date:", class_name="font-medium mb-2"),
                rx.foreach(
                    state.heatmap_dates,
                    lambda date: rx.box(
                        rx.text(date, class_name="text-sm font-medium"),
                        rx.text("Data collected for 24 hours", class_name="text-xs text-gray-500"),
                        class_name="py-2 border-b border-gray-200 dark:border-gray-700"
                    )
                ),
                class_name="space-y-2"
            ),
            rx.text("No data available", class_name="text-gray-500")
        ),
        
        # Legend
        rx.box(
            rx.text("Success Rate Legend:", class_name="text-sm font-medium mr-4"),
            rx.box(
                rx.box(class_name="inline-block w-4 h-4 bg-green-500 mr-1"),
                rx.text("≥95%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-blue-500 mr-1"),
                rx.text("≥80%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-amber-500 mr-1"),
                rx.text("≥60%", class_name="text-xs mr-3"),
                rx.box(class_name="inline-block w-4 h-4 bg-red-500 mr-1"),
                rx.text("<60%", class_name="text-xs"),
                class_name="flex items-center"
            ),
            class_name="flex items-center mt-4"
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )