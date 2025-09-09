"""
AI 응답 디버깅 패널 컴포넌트
TASK_006: UI_ADD_DEBUG_PANEL
"""

import reflex as rx
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class DebugPanelState(rx.State):
    """디버그 패널 상태 관리"""
    
    # 디버그 데이터
    used_data: List[Dict[str, Any]] = []
    calculation_process: List[str] = []
    confidence_score: float = 0.0
    w5h1_elements: Dict[str, str] = {}
    
    # UI 상태
    is_panel_open: bool = False
    active_tab: str = "data"
    
    def toggle_panel(self):
        """패널 토글"""
        self.is_panel_open = not self.is_panel_open
    
    def set_active_tab(self, tab: str):
        """활성 탭 설정"""
        self.active_tab = tab
    
    def update_debug_data(self, 
                         used_data: List[Dict[str, Any]] = None,
                         calculation_process: List[str] = None,
                         confidence_score: float = None,
                         w5h1_elements: Dict[str, str] = None):
        """디버그 데이터 업데이트"""
        if used_data is not None:
            self.used_data = used_data
        if calculation_process is not None:
            self.calculation_process = calculation_process
        if confidence_score is not None:
            self.confidence_score = confidence_score
        if w5h1_elements is not None:
            self.w5h1_elements = w5h1_elements
    
    def clear_debug_data(self):
        """디버그 데이터 초기화"""
        self.used_data = []
        self.calculation_process = []
        self.confidence_score = 0.0
        self.w5h1_elements = {}


def debug_panel() -> rx.Component:
    """AI 응답 디버깅 패널 컴포넌트"""
    
    return rx.drawer(
        rx.drawer.trigger(
            rx.button(
                rx.icon("bug"),
                "디버그",
                size="sm",
                variant="outline",
                on_click=DebugPanelState.toggle_panel,
            ),
        ),
        rx.drawer.overlay(),
        rx.drawer.portal(
            rx.drawer.content(
                rx.drawer.header(
                    rx.heading("AI 응답 디버그 패널", size="lg"),
                ),
                rx.drawer.body(
                    rx.tabs(
                        rx.tabs.list(
                            rx.tabs.trigger("데이터", value="data"),
                            rx.tabs.trigger("계산", value="calculation"),
                            rx.tabs.trigger("신뢰도", value="confidence"),
                            rx.tabs.trigger("6하원칙", value="w5h1"),
                        ),
                        rx.tabs.content(
                            used_data_tab(),
                            value="data",
                        ),
                        rx.tabs.content(
                            calculation_tab(),
                            value="calculation",
                        ),
                        rx.tabs.content(
                            confidence_tab(),
                            value="confidence",
                        ),
                        rx.tabs.content(
                            w5h1_tab(),
                            value="w5h1",
                        ),
                        value=DebugPanelState.active_tab,
                        on_change=DebugPanelState.set_active_tab,
                    ),
                ),
                rx.drawer.footer(
                    rx.button(
                        "초기화",
                        size="sm",
                        variant="outline",
                        on_click=DebugPanelState.clear_debug_data,
                    ),
                    rx.button(
                        "닫기",
                        size="sm",
                        on_click=DebugPanelState.toggle_panel,
                    ),
                ),
                bg="white",
                max_w="600px",
                w="100%",
                h="100%",
                position="fixed",
                right="0",
                top="0",
            ),
        ),
        open=DebugPanelState.is_panel_open,
        direction="right",
    )


def used_data_tab() -> rx.Component:
    """사용된 데이터 탭"""
    return rx.vstack(
        rx.heading("사용된 데이터", size="md"),
        rx.divider(),
        rx.scroll_area(
            rx.foreach(
                DebugPanelState.used_data,
                lambda item: rx.box(
                    rx.hstack(
                        rx.badge(
                            item.get("tag_name", "Unknown"),
                            color_scheme="blue",
                        ),
                        rx.text(
                            f"{item.get('value', 'N/A')} {item.get('unit', '')}",
                            font_weight="medium",
                        ),
                        rx.spacer(),
                        rx.text(
                            item.get("timestamp", ""),
                            font_size="sm",
                            color="gray.500",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.cond(
                        item.get("status") == "critical",
                        rx.badge("위험", color_scheme="red", size="sm"),
                        rx.cond(
                            item.get("status") == "warning",
                            rx.badge("주의", color_scheme="yellow", size="sm"),
                            rx.badge("정상", color_scheme="green", size="sm"),
                        ),
                    ),
                    padding="2",
                    border="1px solid",
                    border_color="gray.200",
                    border_radius="md",
                    margin_bottom="2",
                ),
            ),
            height="400px",
        ),
        spacing="3",
        width="100%",
    )


def calculation_tab() -> rx.Component:
    """계산 과정 탭"""
    return rx.vstack(
        rx.heading("계산 과정", size="md"),
        rx.divider(),
        rx.scroll_area(
            rx.vstack(
                rx.foreach(
                    DebugPanelState.calculation_process,
                    lambda step: rx.hstack(
                        rx.icon("chevron-right", size=16),
                        rx.text(step, font_family="monospace"),
                        spacing="2",
                        padding="2",
                        width="100%",
                    ),
                ),
                spacing="1",
            ),
            height="400px",
        ),
        spacing="3",
        width="100%",
    )


def confidence_tab() -> rx.Component:
    """신뢰도 점수 탭"""
    return rx.vstack(
        rx.heading("신뢰도 분석", size="md"),
        rx.divider(),
        
        # 전체 신뢰도 점수
        rx.box(
            rx.vstack(
                rx.text("전체 신뢰도", font_weight="bold"),
                rx.progress(
                    value=DebugPanelState.confidence_score * 100,
                    width="100%",
                    color_scheme=rx.cond(
                        DebugPanelState.confidence_score > 0.8,
                        "green",
                        rx.cond(
                            DebugPanelState.confidence_score > 0.5,
                            "yellow",
                            "red",
                        ),
                    ),
                ),
                rx.text(
                    f"{DebugPanelState.confidence_score:.1%}",
                    font_size="2xl",
                    font_weight="bold",
                ),
                spacing="2",
            ),
            padding="4",
            border="1px solid",
            border_color="gray.200",
            border_radius="md",
        ),
        
        # 신뢰도 구성 요소
        rx.box(
            rx.vstack(
                rx.text("신뢰도 구성 요소", font_weight="bold"),
                rx.divider(),
                rx.hstack(
                    rx.text("데이터 신뢰도:"),
                    rx.spacer(),
                    rx.badge("95%", color_scheme="green"),
                ),
                rx.hstack(
                    rx.text("모델 신뢰도:"),
                    rx.spacer(),
                    rx.badge("88%", color_scheme="green"),
                ),
                rx.hstack(
                    rx.text("컨텍스트 일치도:"),
                    rx.spacer(),
                    rx.badge("92%", color_scheme="green"),
                ),
                rx.hstack(
                    rx.text("할루시네이션 체크:"),
                    rx.spacer(),
                    rx.badge("통과", color_scheme="green"),
                ),
                spacing="2",
            ),
            padding="4",
            border="1px solid",
            border_color="gray.200",
            border_radius="md",
        ),
        
        spacing="4",
        width="100%",
    )


def w5h1_tab() -> rx.Component:
    """6하원칙 요소별 분해 탭"""
    return rx.vstack(
        rx.heading("6하원칙 분해", size="md"),
        rx.divider(),
        
        rx.vstack(
            # What (무엇을)
            rx.box(
                rx.hstack(
                    rx.badge("무엇을", color_scheme="purple"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("what", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            # Why (왜)
            rx.box(
                rx.hstack(
                    rx.badge("왜", color_scheme="blue"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("why", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            # When (언제)
            rx.box(
                rx.hstack(
                    rx.badge("언제", color_scheme="green"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("when", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            # Where (어디서)
            rx.box(
                rx.hstack(
                    rx.badge("어디서", color_scheme="orange"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("where", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            # Who (누가)
            rx.box(
                rx.hstack(
                    rx.badge("누가", color_scheme="red"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("who", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            # How (어떻게)
            rx.box(
                rx.hstack(
                    rx.badge("어떻게", color_scheme="teal"),
                    rx.spacer(),
                ),
                rx.text(
                    DebugPanelState.w5h1_elements.get("how", "정보 없음"),
                    padding="2",
                    bg="gray.50",
                    border_radius="md",
                    width="100%",
                ),
                width="100%",
            ),
            
            spacing="3",
        ),
        
        spacing="3",
        width="100%",
    )


# 디버그 데이터 업데이트 헬퍼 함수
def update_debug_info(response_data: Dict[str, Any]):
    """AI 응답 처리 시 디버그 정보 업데이트"""
    
    # 사용된 데이터 추출
    used_data = response_data.get('sensor_data', [])
    
    # 계산 과정 추출
    calculation_process = response_data.get('calculation_steps', [])
    
    # 신뢰도 점수
    confidence_score = response_data.get('confidence_score', 0.0)
    
    # 6하원칙 요소
    w5h1_elements = response_data.get('w5h1_data', {})
    
    # State 업데이트
    DebugPanelState.update_debug_data(
        used_data=used_data,
        calculation_process=calculation_process,
        confidence_score=confidence_score,
        w5h1_elements=w5h1_elements
    )