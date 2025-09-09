"""
React Grid Heatmap wrapped with HTML/JavaScript
"""

import reflex as rx
import json


def html_react_heatmap(state) -> rx.Component:
    """
    React Grid Heatmap using HTML script injection
    """
    
    # Prepare data as JSON
    heatmap_data = {
        "data": state.heatmap_matrix,
        "xLabels": state.hour_labels,
        "yLabels": state.date_labels
    }
    
    # JavaScript code to render React Grid Heatmap
    heatmap_script = f"""
    <div id="heatmap-container"></div>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/react-grid-heatmap@1.3.0/dist/index.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/react-grid-heatmap@1.3.0/dist/styles.css">
    
    <script>
    (function() {{
        const data = {json.dumps(heatmap_data)};
        
        const HeatMapGrid = window.ReactGridHeatmap.HeatMapGrid;
        const e = React.createElement;
        
        const heatmapElement = e(HeatMapGrid, {{
            data: data.data,
            xLabels: data.xLabels,
            yLabels: data.yLabels,
            cellHeight: "30px",
            square: false,
            xLabelsPos: 'bottom',
            yLabelsPos: 'left',
            cellRender: (x, y, value) => {{
                const ratio = value / 100;
                let bgColor = '#ef4444'; // red
                if (ratio >= 0.95) bgColor = '#22c55e'; // green
                else if (ratio >= 0.8) bgColor = '#3b82f6'; // blue
                else if (ratio >= 0.6) bgColor = '#fbbf24'; // amber
                
                return e('div', {{
                    style: {{
                        width: '100%',
                        height: '100%',
                        backgroundColor: bgColor,
                        opacity: Math.max(0.3, ratio),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '10px',
                        color: 'white',
                        fontWeight: 'bold'
                    }},
                    title: `${{data.yLabels[y]}} ${{data.xLabels[x]}}:00 - ${{value.toFixed(1)}}%`
                }}, Math.round(value));
            }},
            xLabelsStyle: () => ({{
                fontSize: '10px',
                color: '#666'
            }}),
            yLabelsStyle: () => ({{
                fontSize: '10px',
                color: '#666',
                textAlign: 'right',
                paddingRight: '5px'
            }})
        }});
        
        ReactDOM.render(heatmapElement, document.getElementById('heatmap-container'));
    }})();
    </script>
    """
    
    return rx.box(
        rx.heading("Communication Success Rate Heatmap", size="4", class_name="mb-4"),
        
        # Stats
        rx.box(
            rx.text(f"Tag: {state.selected_tag} | Period: {state.selected_days} days | Success Rate: {state.overall_success_rate}%",
                   class_name="text-sm text-gray-600 dark:text-gray-400 mb-4")
        ),
        
        # Inject the heatmap HTML/JS
        rx.html(heatmap_script),
        
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
        
        # Pandas Analytics
        rx.box(
            rx.heading("Pandas Analytics", size="3", class_name="mt-6 mb-3"),
            rx.box(
                rx.text(f"Best Hour: {state.hourly_pattern_stats['best_hour']}", class_name="text-sm"),
                rx.text(f"Worst Hour: {state.hourly_pattern_stats['worst_hour']}", class_name="text-sm"),
                rx.text(f"Std Dev: {state.hourly_pattern_stats['std_dev']}%", class_name="text-sm"),
                class_name="space-y-2 text-blue-600 dark:text-blue-400"
            ),
            class_name="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
        ),
        
        class_name="bg-white dark:bg-gray-800 rounded-lg p-4"
    )