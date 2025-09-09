"""
Custom React Heatmap component wrapper for Reflex
"""

import reflex as rx
from typing import List, Any


class ReactHeatmapGrid(rx.Component):
    """
    Wrapper for react-heatmap-grid npm package
    https://www.npmjs.com/package/react-heatmap-grid
    """
    library = "react-heatmap-grid"
    tag = "HeatmapGrid"
    
    # Component props
    data: rx.Var[List[List[float]]]
    xLabels: rx.Var[List[str]]
    yLabels: rx.Var[List[str]]
    xLabelsLocation: rx.Var[str] = "bottom"
    yLabelsLocation: rx.Var[str] = "left"
    cellHeight: rx.Var[str] = "30px"
    cellStyle: rx.Var[dict] = {}
    xLabelsStyle: rx.Var[dict] = {}
    yLabelsStyle: rx.Var[dict] = {}
    square: rx.Var[bool] = True
    
    def _get_imports(self):
        return {"": "react-heatmap-grid@1.19.0"}


def create_react_heatmap(state) -> rx.Component:
    """Create a React-based heatmap"""
    
    # Transform data for react-heatmap-grid format
    # data needs to be 2D array: [[row1], [row2], ...]
    
    return rx.box(
        rx.heading("React Heatmap Grid", size="4", class_name="mb-4"),
        
        # Install the package first
        ReactHeatmapGrid.create(
            data=state.heatmap_matrix,  # 2D array
            xLabels=state.hour_labels,   # ["00", "01", ... "23"]
            yLabels=state.date_labels,   # ["2025-09-01", ...]
            cellHeight="25px",
            square=True,
            xLabelsStyle={"fontSize": "10px"},
            yLabelsStyle={"fontSize": "10px"},
            cellStyle=lambda x, y, ratio: {
                "background": f"rgb(0, {int(255 * ratio)}, 0)",
                "fontSize": "8px",
                "color": "white"
            }
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )


def plotly_heatmap(state) -> rx.Component:
    """Alternative: Use Plotly heatmap which is well-supported"""
    
    import plotly.graph_objects as go
    
    # Create plotly figure
    fig = go.Figure(data=go.Heatmap(
        z=state.heatmap_matrix,
        x=state.hour_labels,
        y=state.date_labels,
        colorscale='RdYlGn',
        reversescale=True,
        zmin=0,
        zmax=100,
        text=state.heatmap_matrix,
        texttemplate="%{text:.0f}%",
        textfont={"size": 8},
        colorbar=dict(title="Success Rate %")
    ))
    
    fig.update_layout(
        title="Communication Success Rate Heatmap",
        xaxis_title="Hour of Day",
        yaxis_title="Date",
        height=400
    )
    
    return rx.plotly(data=fig, height="400px")