"""
Communication success rate monitoring page
Shows hourly data collection statistics as a heatmap
"""

import reflex as rx
from ksys_app.states.communication_state import CommunicationState
from ksys_app.components.wrapped_heatmap import wrapped_grid_heatmap
from ksys_app.components.layout import shell


def stats_card(title: str, value: str, subtitle: str = "", color: str = "blue") -> rx.Component:
    """Create a statistics card"""
    
    bg_colors = {
        "green": "bg-green-50 dark:bg-green-900/20",
        "blue": "bg-blue-50 dark:bg-blue-900/20",
        "amber": "bg-amber-50 dark:bg-amber-900/20",
        "red": "bg-red-50 dark:bg-red-900/20"
    }
    
    text_colors = {
        "green": "text-green-600 dark:text-green-400",
        "blue": "text-blue-600 dark:text-blue-400",
        "amber": "text-amber-600 dark:text-amber-400",
        "red": "text-red-600 dark:text-red-400"
    }
    
    return rx.box(
        rx.text(title, class_name="text-sm text-gray-600 dark:text-gray-400"),
        rx.text(value, class_name=f"text-2xl font-bold {text_colors.get(color, text_colors['blue'])}"),
        rx.cond(
            subtitle != "",
            rx.text(subtitle, class_name="text-xs text-gray-500 dark:text-gray-500 mt-1"),
            rx.box()
        ),
        class_name=f"p-4 rounded-lg {bg_colors.get(color, bg_colors['blue'])}"
    )


def daily_trend_chart() -> rx.Component:
    """Daily success rate trend chart"""
    
    return rx.box(
        rx.heading("Daily Trend", size="4", class_name="mb-4"),
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="success_rate",
                stroke="#3b82f6",
                stroke_width=2,
            ),
            rx.recharts.x_axis(data_key="date"),
            rx.recharts.y_axis(domain=[0, 100]),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.tooltip(),
            data=CommunicationState.daily_chart_data,
            height=200,
            class_name="w-full"
        ),
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )


def communication_page() -> rx.Component:
    """Main communication monitoring page - Pandas Enhanced Version"""
    
    return shell(
        rx.box(
            # Header
            rx.box(
                rx.heading("Communication Success Rate Monitor", size="6"),
                rx.text("Real-time monitoring with Pandas-powered analytics", 
                       class_name="text-gray-600 dark:text-gray-400"),
                rx.text(f"Best Hour: {CommunicationState.hourly_pattern_stats['best_hour']} | "
                       f"Worst Hour: {CommunicationState.hourly_pattern_stats['worst_hour']} | "
                       f"Std Dev: {CommunicationState.hourly_pattern_stats['std_dev']}%",
                       class_name="text-sm text-blue-600 dark:text-blue-400 mt-2"),
                class_name="mb-6"
            ),
            
            # Controls
            rx.box(
                # Tag selector
                rx.box(
                    rx.text("Select Sensor:", class_name="text-sm font-medium mb-2"),
                    rx.select(
                        CommunicationState.available_tags,
                        value=CommunicationState.selected_tag,
                        on_change=CommunicationState.set_selected_tag,
                        class_name="w-48"
                    ),
                    class_name="flex flex-col"
                ),
                
                # Period selector with Segmented Control
                rx.box(
                    rx.text("Time Period:", class_name="text-sm font-medium mb-2"),
                    rx.segmented_control.root(
                        rx.segmented_control.item("3 Days", value="3"),
                        rx.segmented_control.item("7 Days", value="7"),
                        rx.segmented_control.item("14 Days", value="14"),
                        rx.segmented_control.item("30 Days", value="30"),
                        value=CommunicationState.selected_days_str,
                        on_change=CommunicationState.set_selected_days_str,
                        default_value="7",
                        size="2",
                    ),
                    class_name="flex flex-col"
                ),
                
                class_name="flex gap-6 items-end mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg"
            ),
            
            # Statistics cards
            rx.box(
                stats_card(
                    "Overall Success Rate",
                    f"{CommunicationState.overall_success_rate}%",
                    f"Last {CommunicationState.selected_days} days",
                    rx.cond(
                        CommunicationState.overall_success_rate >= 95,
                        "green",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 80,
                            "blue",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 60,
                                "amber",
                                "red"
                            )
                        )
                    )
                ),
                stats_card(
                    "Total Records",
                    f"{CommunicationState.total_records:,}",
                    f"Expected: {CommunicationState.expected_records:,}",
                    "blue"
                ),
                stats_card(
                    "Active Hours",
                    CommunicationState.active_hours_str,
                    CommunicationState.total_hours_str,
                    "blue"
                ),
                stats_card(
                    "Data Quality",
                    rx.cond(
                        CommunicationState.overall_success_rate >= 95,
                        "Excellent",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 80,
                            "Good",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 60,
                                "Warning",
                                "Critical"
                            )
                        )
                    ),
                    f"{CommunicationState.selected_tag} sensor",
                    rx.cond(
                        CommunicationState.overall_success_rate >= 95,
                        "green",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 80,
                            "blue",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 60,
                                "amber",
                                "red"
                            )
                        )
                    )
                ),
                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
            ),
            
            # Main heatmap
            rx.box(
                rx.cond(
                    CommunicationState.loading,
                    rx.box(
                        rx.spinner(size="3"),
                        rx.text("Loading data...", class_name="ml-2"),
                        class_name="flex items-center justify-center py-12"
                    ),
                    wrapped_grid_heatmap(CommunicationState)
                ),
                class_name="mb-6"
            ),
            
            # Daily trend chart
            daily_trend_chart(),
            
            class_name="p-6"
        ),
        on_mount=CommunicationState.initialize,
        active_route="/comm"
    )