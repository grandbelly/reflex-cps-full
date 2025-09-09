"""
State management for communication success rate monitoring - Pandas version
"""

import reflex as rx
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ksys_app.db import q


class CommunicationState(rx.State):
    """Pandas 기반 통신 모니터링 상태 관리"""
    
    # UI Controls
    selected_tag: str = "D100"
    selected_days: int = 7
    loading: bool = False
    
    # Data Storage (내부용)
    available_tags: List[str] = []
    _df_hourly: List[Dict] = []  # DataFrame을 dict list로 저장
    _df_daily: List[Dict] = []
    
    @rx.var
    def selected_days_str(self) -> str:
        """Return selected days as string for radio group"""
        return str(self.selected_days)
    
    @rx.var
    def active_hours_str(self) -> str:
        """Return active hours count as string"""
        return str(len(self.hourly_stats))
    
    @rx.var
    def total_hours_str(self) -> str:
        """Return total hours label"""
        return f"Out of {self.selected_days * 24} hours"
    
    @rx.var
    def heatmap_dates(self) -> List[str]:
        """Return dates for heatmap"""
        return self.heatmap_data.get('dates', [])
    
    @rx.var
    def heatmap_matrix(self) -> List[List[float]]:
        """Return 2D matrix for plotly heatmap"""
        if not self.heatmap_data or 'dates' not in self.heatmap_data:
            return []
        
        matrix = []
        for date in self.heatmap_data['dates']:
            row = self.heatmap_data['data'].get(date, [0] * 24)
            matrix.append(row)
        return matrix
    
    @rx.var
    def hour_labels(self) -> List[str]:
        """Hour labels for heatmap"""
        return [f"{i:02d}" for i in range(24)]
    
    @rx.var
    def date_labels(self) -> List[str]:
        """Date labels for heatmap"""
        return self.heatmap_data.get('dates', [])
    
    def _get_cell_color(self, value: float) -> str:
        """Get color class for cell based on value"""
        if value >= 95:
            return "bg-green-500"
        elif value >= 80:
            return "bg-blue-500"
        elif value >= 60:
            return "bg-amber-500"
        else:
            return "bg-red-500"
    
    def set_selected_days_str(self, days: str):
        """Set selected days from radio group string value"""
        try:
            self.selected_days = int(days)
        except (ValueError, TypeError):
            self.selected_days = 7
    
    async def initialize(self):
        """Initialize the communication state"""
        self.loading = True
        
        # Get available tags
        tags = await get_available_tags()
        if tags:
            self.available_tags = tags
            if not self.selected_tag and tags:
                self.selected_tag = tags[0]
        
        # Load initial data
        await self.refresh_data()
        
        self.loading = False
    
    async def refresh_data(self):
        """Refresh all communication data"""
        if not self.selected_tag:
            return
        
        self.loading = True
        
        # Get heatmap data for selected tag
        heatmap = await communication_heatmap_data(
            tag_name=self.selected_tag,
            days=self.selected_days
        )
        self.heatmap_data = heatmap
        
        # Flatten heatmap data for rendering
        cells = []
        if heatmap and 'dates' in heatmap and 'data' in heatmap:
            for date in heatmap['dates']:
                row_data = heatmap['data'].get(date, [0] * 24)
                for hour, value in enumerate(row_data):
                    cells.append({
                        'date': date,
                        'hour': hour,
                        'value': value,
                        'color': self._get_cell_color(value),
                        'label': f"{date} Hour {hour}: {int(value)}%"
                    })
        self.heatmap_cells = cells
        
        # Get hourly statistics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.selected_days)
        
        stats = await communication_hourly_stats(
            tag_name=self.selected_tag,
            start_date=start_date,
            end_date=end_date
        )
        self.hourly_stats = stats
        
        # Calculate overall statistics
        if stats:
            total_records = sum(s['record_count'] for s in stats)
            expected_records = sum(s['expected_count'] for s in stats)
            self.total_records = total_records
            self.expected_records = expected_records
            if expected_records > 0:
                self.overall_success_rate = round((total_records / expected_records) * 100, 2)
        
        # Get daily summary
        summary = await communication_daily_summary(
            start_date=start_date,
            end_date=end_date
        )
        # Filter for selected tag
        self.daily_summary = [s for s in summary if s['tag_name'] == self.selected_tag]
        
        self.loading = False
    
    async def set_selected_tag(self, tag: str):
        """Set the selected tag and refresh data"""
        self.selected_tag = tag
        await self.refresh_data()
    
    async def set_selected_days(self, days: int):
        """Set the selected time period"""
        self.selected_days = days
        await self.refresh_data()
    
    def get_heatmap_chart_data(self) -> List[Dict]:
        """
        Format heatmap data for Recharts
        Returns data in format suitable for a custom heatmap component
        """
        if not self.heatmap_data or 'data' not in self.heatmap_data:
            return []
        
        chart_data = []
        dates = self.heatmap_data.get('dates', [])
        data = self.heatmap_data.get('data', {})
        
        for date in dates:
            if date in data:
                for hour in range(24):
                    chart_data.append({
                        'date': date,
                        'hour': hour,
                        'value': data[date][hour],
                        'label': f"{date} {hour:02d}:00"
                    })
        
        return chart_data
    
    @rx.var
    def daily_chart_data(self) -> List[Dict]:
        """Format daily summary for line chart"""
        if not self.daily_summary:
            return []
        
        return [
            {
                'date': str(s['date']),
                'success_rate': s['success_rate'],
                'record_count': s['daily_count'],
                'expected': s['expected_daily_count']
            }
            for s in self.daily_summary
        ]
    
    def get_status_color(self, success_rate: float) -> str:
        """Get color based on success rate"""
        if success_rate >= 95:
            return "#10b981"  # green
        elif success_rate >= 80:
            return "#3b82f6"  # blue
        elif success_rate >= 60:
            return "#f59e0b"  # amber
        else:
            return "#ef4444"  # red