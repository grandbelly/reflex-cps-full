"""
Plotly heatmap component - Reflex가 잘 지원하는 방법
"""

import reflex as rx
from typing import List, Dict, Any


def create_plotly_heatmap(state) -> rx.Component:
    """
    Plotly를 사용한 히트맵 생성
    Reflex가 rx.plotly로 잘 지원함
    """
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        rx.plotly(
            data=[{
                "type": "heatmap",
                "z": state.heatmap_matrix,  # 2D array of values
                "x": state.hour_labels,     # Hour labels (0-23)
                "y": state.date_labels,     # Date labels
                "colorscale": [
                    [0, "red"],      # 0% - Red
                    [0.6, "orange"], # 60% - Orange  
                    [0.8, "yellow"], # 80% - Yellow
                    [0.95, "lightgreen"], # 95% - Light Green
                    [1, "green"]     # 100% - Green
                ],
                "zmin": 0,
                "zmax": 100,
                "text": state.heatmap_text,  # Text to display on hover
                "hovertemplate": "%{y} %{x}:00<br>Success Rate: %{z:.1f}%<extra></extra>",
                "colorbar": {
                    "title": "Success Rate %",
                    "thickness": 20,
                    "len": 0.7
                }
            }],
            layout={
                "title": f"Sensor {state.selected_tag} - Last {state.selected_days} Days",
                "xaxis": {
                    "title": "Hour of Day",
                    "tickmode": "linear",
                    "tick0": 0,
                    "dtick": 1
                },
                "yaxis": {
                    "title": "Date",
                    "autorange": "reversed"  # Most recent date at top
                },
                "height": 400,
                "margin": {"l": 100, "r": 50, "t": 50, "b": 50}
            },
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"]
            }
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )