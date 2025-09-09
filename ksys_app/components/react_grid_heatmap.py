"""
React Grid Heatmap component wrapper for Reflex
"""

import reflex as rx
from typing import List, Any, Dict, Optional


class ReactGridHeatmap(rx.Component):
    """
    Wrapper for react-grid-heatmap npm package
    https://www.npmjs.com/package/react-grid-heatmap
    """
    
    library = "react-grid-heatmap"
    tag = "HeatMapGrid"
    
    # Required props
    data: rx.Var[List[List[float]]]  # 2D array of values
    
    # Optional props
    xLabels: rx.Var[Optional[List[str]]] = None
    yLabels: rx.Var[Optional[List[str]]] = None
    cellStyle: rx.Var[Optional[Dict]] = None
    cellHeight: rx.Var[str] = "2rem"
    square: rx.Var[bool] = True
    xLabelsPos: rx.Var[str] = "bottom"
    yLabelsPos: rx.Var[str] = "left"
    xLabelsStyle: rx.Var[Optional[Dict]] = None
    yLabelsStyle: rx.Var[Optional[Dict]] = None
    
    def _get_imports(self) -> Dict:
        return {
            "react": "18.2.0",
            "react-grid-heatmap": "1.3.0"
        }


def create_grid_heatmap(state) -> rx.Component:
    """
    Create React Grid Heatmap with proper styling
    """
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Heatmap Component
        rx.box(
            ReactGridHeatmap.create(
                data=state.heatmap_matrix,
                xLabels=state.hour_labels,
                yLabels=state.date_labels,
                cellHeight="30px",
                square=False,
                xLabelsPos="bottom",
                yLabelsPos="left",
                cellStyle=rx.Var.create(
                    lambda x, y, ratio: {
                        "background": rx.cond(
                            ratio >= 0.95,
                            "rgb(34, 197, 94)",  # green-500
                            rx.cond(
                                ratio >= 0.8,
                                "rgb(59, 130, 246)",  # blue-500
                                rx.cond(
                                    ratio >= 0.6,
                                    "rgb(251, 191, 36)",  # amber-400
                                    "rgb(239, 68, 68)"  # red-500
                                )
                            )
                        ),
                        "fontSize": "11px",
                        "color": "white",
                        "border": "1px solid rgba(255, 255, 255, 0.1)"
                    }
                ),
                xLabelsStyle={
                    "fontSize": "10px",
                    "color": "#666"
                },
                yLabelsStyle={
                    "fontSize": "10px", 
                    "color": "#666"
                }
            ),
            class_name="overflow-x-auto"
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
        
        # Anomaly Detection Section (Pandas 기능 활용)
        rx.cond(
            state.anomaly_detection,
            rx.box(
                rx.heading("Anomalies Detected (Z-score > 2)", size="3", class_name="mt-6 mb-2"),
                rx.foreach(
                    state.anomaly_detection,
                    lambda item: rx.box(
                        rx.text(f"{item['timestamp']}: {item['success_rate']}% (Z-score: {item['z_score']})",
                               class_name="text-sm text-red-600 dark:text-red-400"),
                        class_name="py-1"
                    )
                ),
                class_name="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
            ),
            rx.box()
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )