import reflex as rx
import reflex_chakra as rc
from typing import List, Dict, Any, Optional


def unified_kpi_card(
    tag_name: str,
    value_s: rx.Var | str,
    delta_pct: rx.Var | float,
    delta_s: rx.Var | str,
    status_level: rx.Var | int,
    ts_s: rx.Var | str,
    range_label: rx.Var | str,
    chart_data: Optional[List[Dict[str, Any]]] = None,
    gauge_pct: Optional[float] = None,
    comm_status: Optional[bool] = None,
    comm_text: Optional[str] = None,
    realtime_mode: bool = False,
    realtime_data: Optional[List[Dict[str, Any]]] = None,
    qc_min: Optional[float] = None,
    qc_max: Optional[float] = None,
    on_detail_click: Optional[Any] = None,
    unit: Optional[str] = None,
) -> rx.Component:
    """통합 KPI 카드 컴포넌트"""
    
    # 상태별 색상 매핑
    status_color = rx.cond(
        status_level == 2, "red",
        rx.cond(status_level == 1, "amber", "green")
    )
    
    # 델타 계산을 위한 변수
    d = rx.Var.create(f"Number({delta_pct})")
    is_pos = rx.Var.create(f"({d.to_string()} > 0.01)")
    is_neg = rx.Var.create(f"({d.to_string()} < -0.01)")
    
    # 실제 값에서 숫자만 추출
    numeric_val = rx.Var.create(f"parseFloat(String({value_s}).replace(/[^0-9.-]/g, '')) || 0")
    
    return rx.card(
        rx.vstack(
            # 헤더 섹션
            rx.hstack(
                rx.hstack(
                    # 상태 인디케이터
                    rx.el.div(
                        class_name=rx.cond(
                            status_level == 2, "w-3 h-3 bg-red-500 rounded-full animate-pulse",
                            rx.cond(
                                status_level == 1, "w-3 h-3 bg-amber-500 rounded-full",
                                "w-3 h-3 bg-green-500 rounded-full"
                            )
                        )
                    ),
                    rx.text(
                        tag_name,
                        class_name="text-sm font-semibold text-gray-800 truncate",
                        title=tag_name
                    ),
                    spacing="2"
                ),
                
                # 우측 배지들
                rx.hstack(
                    # QC 범위 배지
                    rx.badge(
                        rx.hstack(
                            rx.icon("ruler", size=10),
                            rx.text(range_label, class_name="text-xs"),
                            spacing="1"
                        ),
                        color_scheme="gray", 
                        variant="soft", 
                        size="1"
                    ),
                    
                    # 통신 상태
                    rx.cond(
                        comm_status != None,
                        rx.badge(
                            rx.hstack(
                                rx.icon(
                                    rx.cond(comm_status, "wifi", "wifi-off"),
                                    size=10
                                ),
                                rx.text(
                                    rx.cond(comm_text != None, comm_text, "연결"),
                                    class_name="text-xs"
                                ),
                                spacing="1"
                            ),
                            color_scheme=rx.cond(comm_status, "green", "red"),
                            variant="solid",
                            size="1"
                        ),
                        rx.fragment()
                    ),
                    
                    
                    spacing="1"
                ),
                
                justify="between",
                width="100%",
                align="center"
            ),
            
            # 게이지 섹션 - Chakra Progress
            rx.center(
                rx.box(
                    rc.circular_progress(
                        rc.circular_progress_label(
                            rx.vstack(
                                rx.text(
                                    value_s,
                                    font_weight="bold",
                                    font_size="lg",
                                    color="gray.800",
                                    transition="all 0.2s ease-in-out"
                                ),
                                rx.text(
                                    rx.cond(unit, unit, ""),
                                    font_size="xs",
                                    color="gray.500"
                                ),
                                spacing="0",
                                align="center"
                            )
                        ),
                        value=gauge_pct,
                        color=rx.cond(
                            status_level == 2, "red.500",
                            rx.cond(status_level == 1, "yellow.500", "green.500")
                        ),
                        size="96px",
                        thickness="8px",
                        track_color="gray.200",
                        transition="all 0.3s ease-in-out"
                    ),
                    position="relative"
                ),
                padding="4"
            ),
            
            # 타임스탬프
            rx.text(
                ts_s,
                class_name="text-xs text-gray-500 text-center"
            ),
            
            # 트렌드 차트
            rx.cond(
                chart_data,
                rx.box(
                    rx.cond(
                        realtime_mode,
                        # 실시간 라인 차트 (고급 버전)
                        rx.recharts.line_chart(
                            # 1) 얇은 그리드 (세로선 제거)
                            rx.recharts.cartesian_grid(
                                stroke="#eef2f7", 
                                stroke_dasharray="3 3", 
                                vertical=False
                            ),
                            # 3) 라인
                            rx.recharts.line(
                                data_key="value",
                                type="monotone",                # 부드럽게(overshoot 거의 없음)
                                stroke="#2563eb",
                                stroke_width=2,
                                stroke_linecap="butt",          # 끝단 두꺼운 점 제거 핵심
                                stroke_linejoin="miter",        # 코너 날카롭게
                                dot={"r": 2, "fill": "none", "stroke": "#2563eb", "strokeWidth": 1.5},  # 배경색 없는 점
                                active_dot={"r": 2},            # hover 시만 아주 작은 점
                                connect_nulls=True,
                                is_animation_active=True,
                                animation_duration=280,
                                animation_easing="ease-out",
                            ),
                            # 4) X축 (여백 0, 폰트 7)
                            rx.recharts.x_axis(
                                data_key="bucket",
                                tick_line=False, 
                                axis_line=False,
                                tick_margin=0,                    # 여백 완전 제거
                                tick={"fontSize": 7, "fill": "#9ca3af", "angle": -45, "textAnchor": "end"},  # 45도 회전 추가
                                interval=0,                       
                                min_tick_gap=0,
                                height=25                         # 회전된 텍스트를 위한 여백
                            ),
                            # 5) Y축(데이터 기반 동적 범위)
                            rx.recharts.y_axis(
                                hide=True,
                                domain=["auto", "auto"],  # 데이터에 맞춰 자동 조정
                                allow_data_overflow=True
                            ),
                            # 6) 툴팁(밝은 모달, 커서 하이라이트)
                            rx.recharts.tooltip(
                                cursor={"stroke": "#2563eb", "strokeOpacity": 0.12, "strokeWidth": 8},
                                content_style={
                                    "borderRadius": 8, 
                                    "border": "1px solid #e5e7eb", 
                                    "backgroundColor": "#fff",
                                    "boxShadow": "0 4px 14px rgba(0,0,0,0.08)"
                                },
                                label_style={"fontSize": 10, "color": "#6b7280"},
                                item_style={"fontSize": 11}
                            ),
                            data=rx.cond(realtime_mode, realtime_data, chart_data),
                            width="100%",
                            height=78,
                            margin={"top": 6, "right": 20, "left": 20, "bottom": 25}  # 회전된 X축 라벨을 위한 여백
                        ),
                        # 기본 바 차트  
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="avg",
                                fill="#10b981",
                                fill_opacity=0.8,
                                radius=[2, 2, 0, 0]
                            ),
                            rx.recharts.x_axis(
                                data_key="bucket",
                                tick_line=False,
                                axis_line=False,
                                tick={"fontSize": 7, "fill": "#9ca3af", "angle": -45, "textAnchor": "end"},  # 45도 회전
                                interval="preserveStartEnd",
                                height=25                         # 회전된 텍스트를 위한 여백
                            ),
                            rx.recharts.tooltip(
                                content_style={
                                    "backgroundColor": "white",
                                    "border": "1px solid #e5e7eb",
                                    "borderRadius": "6px",
                                    "color": "#374151",
                                    "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                                }
                            ),
                            data=chart_data,
                            width="100%",
                            height=60,
                            margin={"top": 5, "right": 5, "left": 5, "bottom": 5}
                        )
                    ),
                    class_name="w-full bg-gray-50 rounded-md p-2"
                ),
                # 차트 데이터 없음
                rx.center(
                    rx.vstack(
                        rx.icon("bar-chart", size=16, color="gray"),
                        rx.text("데이터 없음", class_name="text-xs text-gray-400"),
                        spacing="1"
                    ),
                    height="60px",
                    class_name="border-2 border-dashed border-gray-200 rounded-md"
                )
            ),
            
            # 변화량 표시
            rx.hstack(
                rx.icon(
                    rx.cond(is_pos, "trending-up",
                        rx.cond(is_neg, "trending-down", "minus")
                    ),
                    size=16,
                    color=rx.cond(
                        is_pos, "green",
                        rx.cond(is_neg, "red", "gray")
                    )
                ),
                rx.text(
                    delta_s,
                    class_name=rx.cond(
                        is_pos, "text-sm font-medium text-green-600",
                        rx.cond(is_neg, "text-sm font-medium text-red-600", "text-sm font-medium text-gray-500")
                    )
                ),
                spacing="2",
                justify="center"
            ),
            
            
            spacing="3",
            align="center",
            width="100%"
        ),
        
        variant="surface",
        size="2",
        class_name=rx.cond(
            status_level == 2,
            "border-red-500 border-2 shadow-red-500/20 shadow-lg animate-pulse cursor-pointer",
            rx.cond(
                status_level == 1,
                "border-amber-500 border-2 shadow-amber-500/20 cursor-pointer hover:shadow-lg transition-all duration-200",
                "border-gray-200 cursor-pointer hover:shadow-lg hover:bg-gray-50 transition-all duration-200"
            )
        ),
        on_click=on_detail_click
    )




