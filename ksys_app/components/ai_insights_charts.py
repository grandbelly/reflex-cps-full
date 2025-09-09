"""
📊 AI Insights Dashboard Charts Components
AI 인사이트 대시보드용 차트 컴포넌트
"""

import reflex as rx


def prediction_timeline_chart() -> rx.Component:
    """경고 예측 타임라인 차트"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="probability",
                stroke="#ef4444",
                stroke_width=2,
                name="확률(%)"
            ),
            rx.recharts.x_axis(
                data_key="time",
                angle=-45,
                text_anchor="end",
                height=60
            ),
            rx.recharts.y_axis(
                domain=[0, 100]
            ),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.tooltip(),
            rx.recharts.legend(),
            data=AIInsightsState.alert_timeline_data,
            width="100%",
            height=300
        ),
        class_name="w-full"
    )


def anomaly_heatmap() -> rx.Component:
    """실시간 이상 히트맵"""
    from ..states.ai_insights_state import AIInsightsState
    
    # 간단한 히트맵을 그리드로 구현
    return rx.el.div(
        # 센서 목록
        rx.el.div(
            rx.foreach(
                AIInsightsState.anomaly_sensors,
                lambda sensor: rx.el.div(
                    sensor,
                    class_name="text-xs font-medium p-2 text-center border rounded"
                )
            ),
            class_name="grid grid-cols-5 gap-1 mb-4"
        ),
        
        # 히트맵 데이터
        rx.el.div(
            rx.foreach(
                AIInsightsState.anomaly_data,
                lambda item: rx.el.div(
                    rx.el.div(
                        item['sensor'],
                        class_name="text-xs text-white font-medium"
                    ),
                    class_name="p-4 bg-orange-500 rounded text-center",
                    title=item['sensor']
                )
            ),
            class_name="grid grid-cols-5 gap-1"
        ),
        
        # 범례
        rx.el.div(
            rx.el.span("심각도: ", class_name="text-xs text-gray-600 mr-2"),
            rx.el.span("■", class_name="text-yellow-500 mr-1"),
            rx.el.span("낮음", class_name="text-xs mr-3"),
            rx.el.span("■", class_name="text-orange-500 mr-1"),
            rx.el.span("중간", class_name="text-xs mr-3"),
            rx.el.span("■", class_name="text-red-600 mr-1"),
            rx.el.span("높음", class_name="text-xs"),
            class_name="flex items-center justify-center mt-4"
        ),
        
        class_name="w-full"
    )


def correlation_matrix() -> rx.Component:
    """센서 상관관계 매트릭스"""
    from ..states.ai_insights_state import AIInsightsState
    
    # Placeholder 상관관계 매트릭스
    sample_correlations = [
        {'from': 'D101', 'to': 'D102', 'value': 0.85},
        {'from': 'D101', 'to': 'D201', 'value': 0.62},
        {'from': 'D102', 'to': 'D201', 'value': 0.73},
        {'from': 'D201', 'to': 'D301', 'value': -0.45},
        {'from': 'D301', 'to': 'D302', 'value': 0.91},
    ]
    
    return rx.el.div(
        rx.el.h3(
            "센서 간 상관계수",
            class_name="text-sm font-medium text-gray-700 mb-3"
        ),
        
        # 상관관계 리스트
        rx.el.div(
            rx.foreach(
                sample_correlations,
                lambda corr: rx.el.div(
                    rx.el.div(
                        rx.el.span(
                            f"{corr['from']} ↔ {corr['to']}",
                            class_name="text-xs font-medium"
                        ),
                        rx.el.span(
                            f"{corr['value']:.2f}",
                            class_name="text-xs font-bold text-blue-600"
                        ),
                        class_name="flex items-center justify-between"
                    ),
                    
                    # 상관관계 바 (고정 너비로 단순화)
                    rx.el.div(
                        rx.el.div(
                            class_name="h-2 bg-blue-500 rounded",
                            style={"width": "60%"}  # 고정 너비
                        ),
                        class_name="w-full bg-gray-200 rounded h-2"
                    ),
                    
                    class_name="p-2 bg-gray-50 rounded mb-2"
                )
            ),
            class_name="space-y-2"
        ),
        
        # 설명
        rx.el.div(
            rx.el.p(
                "양의 상관관계(파랑): 함께 증가/감소",
                class_name="text-xs text-gray-600"
            ),
            rx.el.p(
                "음의 상관관계(빨강): 반대로 변화",
                class_name="text-xs text-gray-600"
            ),
            class_name="mt-3 p-2 bg-blue-50 rounded"
        ),
        
        class_name="w-full"
    )


def health_trend_chart() -> rx.Component:
    """장비 건강도 트렌드 차트"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.recharts.bar_chart(
            rx.recharts.bar(
                data_key="health",
                fill="#10b981",
                name="건강도(%)"
            ),
            rx.recharts.x_axis(
                data_key="equipment",
                angle=-45,
                text_anchor="end",
                height=80
            ),
            rx.recharts.y_axis(
                domain=[0, 100]
            ),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
            rx.recharts.tooltip(),
            rx.recharts.legend(),
            # 기준선 추가
            rx.recharts.reference_line(
                y=60,
                stroke="#f59e0b",
                stroke_dasharray="5 5",
                label="경고 수준"
            ),
            rx.recharts.reference_line(
                y=30,
                stroke="#ef4444",
                stroke_dasharray="5 5",
                label="위험 수준"
            ),
            data=AIInsightsState.health_trend_data,
            width="100%",
            height=300
        ),
        class_name="w-full"
    )