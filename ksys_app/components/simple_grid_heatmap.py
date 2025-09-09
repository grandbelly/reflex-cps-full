"""
Simple Grid Heatmap that works with Reflex
"""

import reflex as rx


def simple_grid_heatmap(state) -> rx.Component:
    """
    Simple grid heatmap using Reflex components
    """
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Display stats
        rx.box(
            rx.text(f"Tag: {state.selected_tag}", class_name="text-sm"),
            rx.text(f"Period: {state.selected_days} days", class_name="text-sm"),
            rx.text(f"Overall Success Rate: {state.overall_success_rate}%", 
                   class_name="text-sm font-bold"),
            class_name="mb-4 space-y-1 text-gray-600 dark:text-gray-400"
        ),
        
        # Hour labels
        rx.box(
            rx.box(class_name="w-20"),  # Empty corner
            *[
                rx.text(f"{h:02d}", class_name="text-xs text-center w-8")
                for h in range(24)
            ],
            class_name="flex gap-0.5 mb-1"
        ),
        
        # Grid rows
        rx.foreach(
            state.date_labels,
            lambda date: rx.box(
                rx.text(date[-5:], class_name="text-xs w-20 pr-2 text-right"),
                rx.foreach(
                    range(24),
                    lambda hour: rx.box(
                        class_name=rx.cond(
                            state.heatmap_matrix[state.date_labels.index(date)][hour] >= 95,
                            "w-8 h-8 bg-green-500",
                            rx.cond(
                                state.heatmap_matrix[state.date_labels.index(date)][hour] >= 80,
                                "w-8 h-8 bg-blue-500",
                                rx.cond(
                                    state.heatmap_matrix[state.date_labels.index(date)][hour] >= 60,
                                    "w-8 h-8 bg-amber-400",
                                    "w-8 h-8 bg-red-500"
                                )
                            )
                        ),
                        style={
                            "opacity": rx.cond(
                                state.heatmap_matrix[state.date_labels.index(date)][hour] > 0,
                                state.heatmap_matrix[state.date_labels.index(date)][hour] / 100,
                                0.1
                            )
                        }
                    )
                ),
                class_name="flex gap-0.5"
            )
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
        
        # Pandas Analytics Section
        rx.box(
            rx.heading("Analytics (Pandas Powered)", size="3", class_name="mt-6 mb-3"),
            rx.box(
                rx.text(f"📊 Best Hour: {state.hourly_pattern_stats['best_hour']}", 
                       class_name="text-sm"),
                rx.text(f"📉 Worst Hour: {state.hourly_pattern_stats['worst_hour']}", 
                       class_name="text-sm"),
                rx.text(f"📈 Std Deviation: {state.hourly_pattern_stats['std_dev']}%", 
                       class_name="text-sm"),
                class_name="space-y-2"
            ),
            class_name="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
        ),
        
        # Anomaly Detection
        rx.cond(
            state.anomaly_detection,
            rx.box(
                rx.heading("⚠️ Anomalies Detected", size="3", class_name="mb-2"),
                rx.foreach(
                    state.anomaly_detection[:5],  # Show top 5
                    lambda item: rx.text(
                        f"{item['timestamp']}: {item['success_rate']}% (Z-score: {item['z_score']})",
                        class_name="text-sm text-red-600 dark:text-red-400"
                    )
                ),
                class_name="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
            ),
            rx.box()
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4 overflow-x-auto"
    )