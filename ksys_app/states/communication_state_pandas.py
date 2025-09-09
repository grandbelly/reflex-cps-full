"""
Communication monitoring with Pandas - 훨씬 더 간단한 버전
"""

import reflex as rx
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ksys_app.db import q


class CommunicationStatePandas(rx.State):
    """Pandas를 사용한 통신 모니터링 상태 관리"""
    
    # UI Controls
    selected_tag: str = "D100"
    selected_days: int = 7
    loading: bool = False
    
    # Data
    df_hourly: pd.DataFrame = pd.DataFrame()
    df_daily: pd.DataFrame = pd.DataFrame()
    available_tags: List[str] = []
    
    @rx.var
    def heatmap_plotly_data(self) -> Dict[str, Any]:
        """Pandas로 Plotly 히트맵 데이터 생성"""
        
        if self.df_hourly.empty:
            return {
                "z": [],
                "x": [f"{i:02d}" for i in range(24)],
                "y": []
            }
        
        # Pivot table로 간단하게 히트맵 매트릭스 생성
        df = pd.DataFrame(self.df_hourly)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Pivot: 행=날짜, 열=시간, 값=성공률
        pivot = df.pivot_table(
            values='success_rate',
            index='date',
            columns='hour',
            fill_value=0
        )
        
        return {
            "z": pivot.values.tolist(),  # 2D 매트릭스
            "x": [f"{i:02d}" for i in range(24)],  # 시간 라벨
            "y": [str(date) for date in pivot.index]  # 날짜 라벨
        }
    
    @rx.var
    def statistics(self) -> Dict[str, Any]:
        """Pandas로 통계 계산"""
        
        if self.df_hourly.empty:
            return {
                "overall_success_rate": 0,
                "total_records": 0,
                "expected_records": 0,
                "active_hours": 0,
                "avg_daily_rate": 0,
                "std_dev": 0
            }
        
        df = pd.DataFrame(self.df_hourly)
        
        # 기본 통계
        total_records = df['record_count'].sum()
        expected_records = df['expected_count'].sum()
        overall_rate = (total_records / expected_records * 100) if expected_records > 0 else 0
        
        # 추가 통계 (Pandas 사용하면 쉽게 계산)
        return {
            "overall_success_rate": round(overall_rate, 2),
            "total_records": int(total_records),
            "expected_records": int(expected_records),
            "active_hours": len(df),
            "avg_daily_rate": round(df.groupby(pd.to_datetime(df['timestamp']).dt.date)['success_rate'].mean().mean(), 2),
            "std_dev": round(df['success_rate'].std(), 2),
            "min_rate": round(df['success_rate'].min(), 2),
            "max_rate": round(df['success_rate'].max(), 2),
            "median_rate": round(df['success_rate'].median(), 2)
        }
    
    @rx.var
    def daily_trend_data(self) -> List[Dict]:
        """일별 트렌드 데이터"""
        
        if self.df_daily.empty:
            return []
        
        df = pd.DataFrame(self.df_daily)
        df = df[df['tag_name'] == self.selected_tag].copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%m-%d')
        
        return df[['date', 'success_rate']].to_dict('records')
    
    @rx.var
    def hourly_pattern(self) -> List[Dict]:
        """시간대별 평균 패턴 분석"""
        
        if self.df_hourly.empty:
            return []
        
        df = pd.DataFrame(self.df_hourly)
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # 시간대별 평균 성공률
        hourly_avg = df.groupby('hour').agg({
            'success_rate': ['mean', 'std', 'min', 'max'],
            'record_count': 'sum'
        }).round(2)
        
        result = []
        for hour in range(24):
            if hour in hourly_avg.index:
                result.append({
                    'hour': f"{hour:02d}:00",
                    'avg_rate': hourly_avg.loc[hour, ('success_rate', 'mean')],
                    'std': hourly_avg.loc[hour, ('success_rate', 'std')],
                    'min': hourly_avg.loc[hour, ('success_rate', 'min')],
                    'max': hourly_avg.loc[hour, ('success_rate', 'max')]
                })
            else:
                result.append({
                    'hour': f"{hour:02d}:00",
                    'avg_rate': 0,
                    'std': 0,
                    'min': 0,
                    'max': 0
                })
        
        return result
    
    async def refresh_data_pandas(self):
        """Pandas를 사용한 데이터 갱신"""
        
        self.loading = True
        
        # 날짜 범위 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.selected_days)
        
        # 시간별 데이터 쿼리
        query_hourly = """
        WITH hourly_data AS (
            SELECT 
                date_trunc('hour', ts) as timestamp,
                tag_name,
                COUNT(*) as record_count,
                720 as expected_count  -- 5초 간격
            FROM influx_hist
            WHERE ts >= %s AND ts < %s AND tag_name = %s
            GROUP BY date_trunc('hour', ts), tag_name
        )
        SELECT 
            timestamp,
            tag_name,
            record_count,
            expected_count,
            ROUND((record_count::NUMERIC / expected_count) * 100, 2) as success_rate
        FROM hourly_data
        ORDER BY timestamp DESC
        """
        
        result_hourly = await q(query_hourly, (start_date, end_date, self.selected_tag))
        self.df_hourly = pd.DataFrame(result_hourly) if result_hourly else pd.DataFrame()
        
        # 일별 데이터 쿼리
        query_daily = """
        WITH daily_data AS (
            SELECT 
                date_trunc('day', ts) as date,
                tag_name,
                COUNT(*) as daily_count,
                17280 as expected_daily_count  -- 24시간 * 720
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
        self.df_daily = pd.DataFrame(result_daily) if result_daily else pd.DataFrame()
        
        self.loading = False
    
    async def analyze_anomalies(self) -> Dict[str, Any]:
        """Pandas로 이상치 탐지"""
        
        if self.df_hourly.empty:
            return {"anomalies": [], "insights": []}
        
        df = pd.DataFrame(self.df_hourly)
        
        # Z-score로 이상치 탐지
        df['z_score'] = np.abs((df['success_rate'] - df['success_rate'].mean()) / df['success_rate'].std())
        anomalies = df[df['z_score'] > 2]  # Z-score > 2인 경우 이상치
        
        # 시간대별 패턴 분석
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['weekday'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        
        # 인사이트 생성
        insights = []
        
        # 가장 안정적인 시간대
        hourly_std = df.groupby('hour')['success_rate'].std()
        most_stable_hour = hourly_std.idxmin()
        insights.append(f"가장 안정적인 시간대: {most_stable_hour:02d}:00")
        
        # 주중/주말 비교
        weekday_avg = df[df['weekday'] < 5]['success_rate'].mean()
        weekend_avg = df[df['weekday'] >= 5]['success_rate'].mean()
        insights.append(f"주중 평균: {weekday_avg:.1f}%, 주말 평균: {weekend_avg:.1f}%")
        
        return {
            "anomalies": anomalies[['timestamp', 'success_rate', 'z_score']].to_dict('records'),
            "insights": insights
        }