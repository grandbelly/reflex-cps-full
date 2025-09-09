"""
🎴 AI Insights Dashboard Cards Components
AI 인사이트 대시보드용 카드 컴포넌트
"""

import reflex as rx
from typing import Dict, List


def alert_prediction_card() -> rx.Component:
    """경고 예측 카드"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.foreach(
            AIInsightsState.high_risk_sensors[:3],
            lambda alert: rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.span(
                            alert['sensor'],
                            class_name="font-semibold text-sm"
                        ),
                        rx.el.span(
                            f"{alert['probability']}%",
                            class_name="text-xs px-2 py-1 bg-red-100 text-red-700 rounded-full ml-2"
                        ),
                        class_name="flex items-center justify-between"
                    ),
                    rx.el.div(
                        rx.el.span("예측 시간: ", class_name="text-xs text-gray-500"),
                        rx.el.span(
                            alert['predicted_time'],
                            class_name="text-xs font-medium"
                        ),
                        class_name="mt-1"
                    ),
                    class_name="mb-2"
                ),
                
                # 위험 요소 및 권장 조치 (간단하게 표시)
                rx.el.div(
                    rx.el.p("위험도 상세", class_name="text-xs text-gray-600 mb-1"),
                    rx.el.p(
                        f"경고 유형: {alert.get('alert_type', 'N/A')}",
                        class_name="text-xs text-gray-700 ml-2"
                    ),
                    class_name="mb-2"
                ),
                
                class_name="p-3 border-l-4 border-red-500 bg-red-50 rounded mb-3"
            )
        ),
        class_name="max-h-96 overflow-y-auto"
    )


def anomaly_detection_card() -> rx.Component:
    """이상 감지 카드"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.foreach(
            AIInsightsState.detected_anomalies[:5],
            lambda anomaly: rx.el.div(
                rx.el.div(
                    rx.el.span(
                        anomaly['sensor'],
                        class_name="font-medium text-sm"
                    ),
                    rx.el.span(
                        anomaly['severity'],
                        class_name="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded-full ml-2"
                    ),
                    class_name="flex items-center justify-between mb-1"
                ),
                rx.el.div(
                    rx.el.span("값: ", class_name="text-xs text-gray-500"),
                    rx.el.span(anomaly['value'], class_name="text-xs font-medium mr-3"),
                    rx.el.span("유형: ", class_name="text-xs text-gray-500"),
                    rx.el.span(anomaly['anomaly_type'], class_name="text-xs font-medium"),
                    class_name="mb-1"
                ),
                rx.el.div(
                    anomaly['description'],
                    class_name="text-xs text-gray-600"
                ),
                rx.el.div(
                    rx.el.span(f"신뢰도: {anomaly['confidence']}%", class_name="text-xs text-gray-500"),
                    rx.el.span(f" • {anomaly['timestamp']}", class_name="text-xs text-gray-400"),
                    class_name="mt-1"
                ),
                class_name="p-3 border-l-4 border-orange-500 bg-orange-50 rounded mb-3"
            )
        ),
        class_name="max-h-96 overflow-y-auto"
    )


def maintenance_schedule_card() -> rx.Component:
    """유지보수 일정 카드"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("장비", class_name="text-xs text-left p-2"),
                    rx.el.th("유형", class_name="text-xs text-left p-2"),
                    rx.el.th("우선순위", class_name="text-xs text-left p-2"),
                    rx.el.th("예정일", class_name="text-xs text-left p-2"),
                    rx.el.th("소요시간", class_name="text-xs text-left p-2"),
                    rx.el.th("비용", class_name="text-xs text-left p-2"),
                    rx.el.th("ROI", class_name="text-xs text-left p-2"),
                    class_name="border-b"
                )
            ),
            rx.el.tbody(
                rx.foreach(
                    AIInsightsState.maintenance_schedule,
                    lambda item: rx.el.tr(
                        rx.el.td(item['equipment'], class_name="text-xs p-2"),
                        rx.el.td(
                            item['type'],
                            class_name="text-xs p-2"
                        ),
                        rx.el.td(
                            rx.el.span(
                                item['priority'],
                                class_name="text-xs px-2 py-1 bg-yellow-100 text-yellow-700 rounded"
                            ),
                            class_name="p-2"
                        ),
                        rx.el.td(item['date'], class_name="text-xs p-2"),
                        rx.el.td(item['duration'], class_name="text-xs p-2"),
                        rx.el.td(item['cost'], class_name="text-xs p-2"),
                        rx.el.td(
                            rx.el.span(
                                f"{item['roi']}x",
                                class_name="text-xs text-green-600 font-medium"
                            ),
                            class_name="p-2"
                        ),
                        class_name="hover:bg-gray-50 border-b"
                    )
                )
            ),
            class_name="w-full"
        ),
        class_name="max-h-96 overflow-y-auto"
    )


def equipment_health_card() -> rx.Component:
    """장비 건강도 카드"""
    from ..states.ai_insights_state import AIInsightsState
    
    return rx.el.div(
        rx.foreach(
            AIInsightsState.equipment_health_list,
            lambda equip: rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.span(
                            equip['equipment'],
                            class_name="font-medium text-sm"
                        ),
                        rx.el.span(
                            f"{equip['health']}%",
                            class_name="text-sm font-bold text-green-600"
                        ),
                        class_name="flex items-center justify-between mb-2"
                    ),
                    
                    # 건강도 바
                    rx.el.div(
                        rx.el.div(
                            class_name="h-2 bg-green-500 rounded",
                            style={"width": f"{equip['health']}%"}
                        ),
                        class_name="w-full bg-gray-200 rounded h-2 mb-2"
                    ),
                    
                    # 상태 정보
                    rx.el.div(
                        rx.el.span("상태: ", class_name="text-xs text-gray-500"),
                        rx.el.span(
                            equip['status'],
                            class_name="text-xs font-medium text-green-600"
                        ),
                        rx.el.span(f" • RUL: {equip['rul']}일", class_name="text-xs text-gray-500 ml-2"),
                        class_name="mb-1"
                    ),
                    
                    rx.el.div(
                        rx.el.span(f"고장확률: {equip['failure_prob']}%", class_name="text-xs text-gray-500"),
                        rx.el.span(f" • 위험도: {equip['risk_score']}/10", class_name="text-xs text-gray-500 ml-2"),
                        class_name="mb-1"
                    )
                ),
                class_name="p-3 bg-gray-50 rounded-lg mb-3 hover:bg-gray-100 transition-colors"
            )
        ),
        class_name="max-h-96 overflow-y-auto"
    )