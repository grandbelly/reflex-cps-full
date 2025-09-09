"""
Properly wrapped React Grid Heatmap for Reflex
"""

import reflex as rx
from typing import List, Dict, Any


class HeatMapGrid(rx.Component):
    """React Grid Heatmap Component"""
    
    library = "react-grid-heatmap@1.3.0"
    tag = "HeatMapGrid"
    
    # Props
    data: rx.Var[List[List[float]]]
    xLabels: rx.Var[List[str]]
    yLabels: rx.Var[List[str]]
    cellHeight: rx.Var[str] = "30px"
    square: rx.Var[bool] = False
    xLabelsPos: rx.Var[str] = "bottom"
    yLabelsPos: rx.Var[str] = "left"


def wrapped_grid_heatmap(state) -> rx.Component:
    """
    Wrapped React Grid Heatmap with Pandas analytics
    """
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Heatmap Stats
        rx.box(
            rx.badge(f"Tag: {state.selected_tag}", color="blue"),
            rx.badge(f"Period: {state.selected_days} days", color="green"),
            rx.badge(
                f"Success: {state.overall_success_rate}%",
                color=rx.cond(
                    state.overall_success_rate >= 95, "green",
                    rx.cond(
                        state.overall_success_rate >= 80, "blue",
                        rx.cond(
                            state.overall_success_rate >= 60, "yellow",
                            "red"
                        )
                    )
                )
            ),
            class_name="flex gap-2 mb-4"
        ),
        
        # The Heatmap Component
        rx.box(
            HeatMapGrid.create(
                data=state.heatmap_matrix,
                xLabels=state.hour_labels,
                yLabels=state.date_labels,
                cellHeight="30px",
                square=False
            ),
            class_name="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg p-2"
        ),
        
        # Legend
        rx.box(
            rx.box(
                rx.box(class_name="w-4 h-4 bg-green-500"),
                rx.text("≥95%", class_name="text-xs"),
                class_name="flex items-center gap-1"
            ),
            rx.box(
                rx.box(class_name="w-4 h-4 bg-blue-500"),
                rx.text("≥80%", class_name="text-xs"),
                class_name="flex items-center gap-1"
            ),
            rx.box(
                rx.box(class_name="w-4 h-4 bg-amber-400"),
                rx.text("≥60%", class_name="text-xs"),
                class_name="flex items-center gap-1"
            ),
            rx.box(
                rx.box(class_name="w-4 h-4 bg-red-500"),
                rx.text("<60%", class_name="text-xs"),
                class_name="flex items-center gap-1"
            ),
            class_name="flex gap-4 mt-4 justify-center"
        ),
        
        # Pandas-powered Analytics
        rx.box(
            rx.heading("📊 Pandas Analytics", size="3", class_name="mb-3"),
            rx.box(
                rx.box(
                    rx.text("Best Hour", class_name="text-sm text-gray-600"),
                    rx.text(state.hourly_pattern_stats['best_hour'], class_name="text-xl font-bold text-green-600"),
                    rx.text("Highest success rate", class_name="text-xs text-gray-500"),
                    class_name="text-center"
                ),
                rx.box(
                    rx.text("Worst Hour", class_name="text-sm text-gray-600"),
                    rx.text(state.hourly_pattern_stats['worst_hour'], class_name="text-xl font-bold text-red-600"),
                    rx.text("Lowest success rate", class_name="text-xs text-gray-500"),
                    class_name="text-center"
                ),
                rx.box(
                    rx.text("Std Deviation", class_name="text-sm text-gray-600"),
                    rx.text(f"{state.hourly_pattern_stats['std_dev']}%", class_name="text-xl font-bold text-blue-600"),
                    rx.text("Data variability", class_name="text-xs text-gray-500"),
                    class_name="text-center"
                ),
                class_name="grid grid-cols-3 gap-4"
            ),
            class_name="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg"
        ),
        
        # Anomaly Detection Results
        rx.cond(
            state.anomaly_detection,
            rx.box(
                rx.heading("⚠️ Anomalies (Z-score > 2)", size="3", class_name="mb-3"),
                rx.box(
                    rx.foreach(
                        state.anomaly_detection[:5],
                        lambda item: rx.box(
                            rx.text(item['timestamp'], class_name="font-medium"),
                            rx.text(f"{item['success_rate']}%", class_name="text-red-600"),
                            rx.text(f"Z: {item['z_score']}", class_name="text-gray-500 text-sm"),
                            class_name="flex justify-between items-center py-2 border-b"
                        )
                    ),
                    class_name="space-y-1"
                ),
                class_name="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg"
            ),
            rx.box()
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-6"
    )