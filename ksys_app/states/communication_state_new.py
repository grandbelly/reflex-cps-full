"""
Communication monitoring with Pandas - Clean version
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
        """Radio group용 문자열 변환"""
        return str(self.selected_days)
    
    @rx.var
    def active_hours_str(self) -> str:
        """활성 시간 수"""
        return str(len(self._df_hourly))
    
    @rx.var
    def total_hours_str(self) -> str:
        """전체 시간 라벨"""
        return f"Out of {self.selected_days * 24} hours"
    
    @rx.var
    def overall_success_rate(self) -> float:
        """전체 성공률 계산 (Pandas)"""
        if not self._df_hourly:
            return 0.0
        
        df = pd.DataFrame(self._df_hourly)
        total_records = df['record_count'].sum()
        expected_records = df['expected_count'].sum()
        
        if expected_records > 0:
            return round((total_records / expected_records) * 100, 2)
        return 0.0
    
    @rx.var
    def total_records(self) -> int:
        """전체 레코드 수"""
        if not self._df_hourly:
            return 0
        df = pd.DataFrame(self._df_hourly)
        return int(df['record_count'].sum())
    
    @rx.var
    def expected_records(self) -> int:
        """예상 레코드 수"""
        if not self._df_hourly:
            return 0
        df = pd.DataFrame(self._df_hourly)
        return int(df['expected_count'].sum())
    
    @rx.var
    def heatmap_matrix(self) -> List[List[float]]:
        """Pandas pivot_table로 히트맵 매트릭스 생성"""
        if not self._df_hourly:
            return [[0] * 24 for _ in range(self.selected_days)]
        
        df = pd.DataFrame(self._df_hourly)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        
        # Pivot table로 매트릭스 생성
        pivot = df.pivot_table(
            values='success_rate',
            index='date',
            columns='hour',
            fill_value=0
        )
        
        # 모든 시간(0-23)이 포함되도록 reindex
        pivot = pivot.reindex(columns=range(24), fill_value=0)
        
        return pivot.values.tolist()
    
    @rx.var
    def hour_labels(self) -> List[str]:
        """시간 라벨 (00-23)"""
        return [f"{i:02d}" for i in range(24)]
    
    @rx.var
    def date_labels(self) -> List[str]:
        """날짜 라벨"""
        if not self._df_hourly:
            return []
        
        df = pd.DataFrame(self._df_hourly)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        dates = sorted(df['date'].unique())
        return [str(date) for date in dates]
    
    @rx.var
    def heatmap_dates(self) -> List[str]:
        """히트맵용 날짜 리스트"""
        return self.date_labels
    
    @rx.var
    def daily_chart_data(self) -> List[Dict]:
        """일별 트렌드 차트 데이터"""
        if not self._df_daily:
            return []
        
        df = pd.DataFrame(self._df_daily)
        df = df[df['tag_name'] == self.selected_tag].copy()
        df = df.sort_values('date')
        
        # 날짜 포맷팅
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%m/%d')
        
        return df[['date', 'success_rate']].to_dict('records')
    
    @rx.var
    def hourly_pattern_stats(self) -> Dict[str, Any]:
        """시간대별 패턴 분석 (Pandas 활용)"""
        if not self._df_hourly:
            return {"best_hour": "N/A", "worst_hour": "N/A", "std_dev": 0}
        
        df = pd.DataFrame(self._df_hourly)
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # 시간대별 평균 성공률
        hourly_avg = df.groupby('hour')['success_rate'].mean()
        
        if not hourly_avg.empty:
            best_hour = hourly_avg.idxmax()
            worst_hour = hourly_avg.idxmin()
            std_dev = df['success_rate'].std()
            
            return {
                "best_hour": f"{best_hour:02d}:00",
                "worst_hour": f"{worst_hour:02d}:00",
                "std_dev": round(std_dev, 2)
            }
        
        return {"best_hour": "N/A", "worst_hour": "N/A", "std_dev": 0}
    
    def set_selected_days_str(self, days: str):
        """Radio group에서 선택한 일수 설정"""
        try:
            self.selected_days = int(days)
        except (ValueError, TypeError):
            self.selected_days = 7
    
    async def initialize(self):
        """초기화"""
        self.loading = True
        
        # 태그 목록 가져오기
        query = "SELECT DISTINCT tag_name FROM influx_latest ORDER BY tag_name"
        result = await q(query, ())
        if result:
            self.available_tags = [row['tag_name'] for row in result]
            if not self.selected_tag and self.available_tags:
                self.selected_tag = self.available_tags[0]
        
        # 데이터 로드
        await self.refresh_data()
        self.loading = False
    
    async def refresh_data(self):
        """데이터 새로고침 (Pandas 사용)"""
        self.loading = True
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.selected_days)
        
        # 시간별 데이터 쿼리
        query_hourly = """
        WITH hourly_data AS (
            SELECT 
                date_trunc('hour', ts) as timestamp,
                COUNT(*) as record_count,
                720 as expected_count
            FROM influx_hist
            WHERE ts >= %s AND ts < %s AND tag_name = %s
            GROUP BY date_trunc('hour', ts)
        )
        SELECT 
            timestamp,
            record_count,
            expected_count,
            ROUND((record_count::NUMERIC / expected_count) * 100, 2) as success_rate
        FROM hourly_data
        ORDER BY timestamp DESC
        """
        
        result_hourly = await q(query_hourly, (start_date, end_date, self.selected_tag))
        self._df_hourly = result_hourly if result_hourly else []
        
        # 일별 데이터 쿼리
        query_daily = """
        WITH daily_data AS (
            SELECT 
                date_trunc('day', ts) as date,
                tag_name,
                COUNT(*) as daily_count,
                17280 as expected_daily_count
            FROM influx_hist
            WHERE ts >= %s AND ts < %s
            GROUP BY date_trunc('day', ts), tag_name
        )
        SELECT 
            date,
            tag_name,
            daily_count,
            expected_daily_count,
            ROUND((daily_count::NUMERIC / expected_daily_count) * 100, 2) as success_rate
        FROM daily_data
        ORDER BY date DESC
        """
        
        result_daily = await q(query_daily, (start_date, end_date))
        self._df_daily = result_daily if result_daily else []
        
        self.loading = False
    
    async def set_selected_tag(self, tag: str):
        """태그 선택 및 데이터 갱신"""
        self.selected_tag = tag
        await self.refresh_data()
    
    @rx.var
    def anomaly_detection(self) -> List[Dict]:
        """이상치 탐지 (Z-score 사용)"""
        if not self._df_hourly:
            return []
        
        df = pd.DataFrame(self._df_hourly)
        
        # Z-score 계산
        mean = df['success_rate'].mean()
        std = df['success_rate'].std()
        
        if std > 0:
            df['z_score'] = np.abs((df['success_rate'] - mean) / std)
            anomalies = df[df['z_score'] > 2]  # Z-score > 2는 이상치
            
            if not anomalies.empty:
                anomalies['timestamp'] = pd.to_datetime(anomalies['timestamp']).dt.strftime('%m/%d %H:%M')
                return anomalies[['timestamp', 'success_rate', 'z_score']].round(2).to_dict('records')
        
        return []