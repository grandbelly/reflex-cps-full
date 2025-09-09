#!/usr/bin/env python3
"""
REFLEX_USAGE_GUIDE.md 검증을 위한 테스트 케이스
실제로 동작하는 Reflex 앱으로 가이드의 패턴들을 테스트
"""

import reflex as rx
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime


# 1. 기본 State 클래스 테스트
class BasicState(rx.State):
    """기본 타입 어노테이션 테스트"""
    count: int = 0
    name: str = ""
    items: List[str] = []
    data: Dict[str, Any] = {}
    is_loading: bool = False
    
    @rx.event
    def increment(self):
        self.count += 1
    
    @rx.var
    def double_count(self) -> int:
        return self.count * 2
    
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0


# 2. NaN 처리 테스트
class NaNHandlingState(rx.State):
    """NaN 값 처리 테스트"""
    correlation_data: Dict[str, float] = {}
    processed_data: List[Dict[str, float]] = []
    
    @rx.event
    def test_nan_handling(self):
        """NaN이 포함된 데이터 처리 테스트"""
        # pandas에서 NaN 생성
        df = pd.DataFrame({
            'A': [1, 2, np.nan, 4],
            'B': [5, np.nan, 7, 8],
            'C': [9, 10, 11, np.nan]
        })
        
        # 상관관계 계산 (NaN 발생 가능)
        corr_matrix = df.corr()
        
        # ❌ 잘못된 방법 - NaN이 그대로 전달됨
        # self.correlation_data = corr_matrix.to_dict()
        
        # ✅ 올바른 방법 - NaN 값 사전 처리
        cleaned_corr = corr_matrix.fillna(0.0)
        self.correlation_data = cleaned_corr.to_dict()
        
        # 리스트 데이터도 정제
        self.processed_data = []
        for i, row in df.iterrows():
            row_dict = row.fillna(0.0).to_dict()
            row_dict['index'] = int(i)
            self.processed_data.append(row_dict)
    
    @rx.var
    def correlation_summary(self) -> str:
        if not self.correlation_data:
            return "데이터 없음"
        
        # 상관계수 요약
        correlations = []
        for col1, inner_dict in self.correlation_data.items():
            for col2, value in inner_dict.items():
                if col1 != col2:  # 자기 자신과의 상관관계 제외
                    correlations.append(f"{col1}-{col2}: {value:.3f}")
        
        return " | ".join(correlations[:3])  # 처음 3개만


# 3. 리스트 렌더링 테스트
class ListRenderingState(rx.State):
    """List 렌더링 패턴 테스트"""
    dynamic_items: List[str] = ["초기1", "초기2", "초기3"]
    static_items: List[str] = ["정적1", "정적2", "정적3"]
    complex_items: List[Dict[str, Any]] = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.complex_items = [
            {"name": "아이템1", "value": 10, "active": True},
            {"name": "아이템2", "value": 20, "active": False},
            {"name": "아이템3", "value": 30, "active": True}
        ]
    
    @rx.event
    def add_dynamic_item(self, form_data: dict):
        """동적 아이템 추가"""
        new_item = form_data.get("item", "")
        if new_item:
            self.dynamic_items.append(new_item)
    
    @rx.event
    def remove_item(self, index: int):
        """아이템 제거"""
        if 0 <= index < len(self.dynamic_items):
            self.dynamic_items.pop(index)
    
    @rx.event
    def toggle_complex_item(self, index: int):
        """복합 아이템 토글"""
        if 0 <= index < len(self.complex_items):
            self.complex_items[index]["active"] = not self.complex_items[index]["active"]


# 4. 비동기 처리 테스트
class AsyncState(rx.State):
    """비동기 이벤트 처리 테스트"""
    is_loading: bool = False
    result: str = ""
    progress: int = 0
    error_message: str = ""
    
    @rx.event(background=True)
    async def simulate_async_task(self):
        """비동기 작업 시뮬레이션"""
        async with self:
            self.is_loading = True
            self.result = ""
            self.error_message = ""
            self.progress = 0
        
        try:
            # 시뮬레이션: 5단계 작업
            for i in range(5):
                await asyncio.sleep(1)  # 1초 대기
                async with self:
                    self.progress = (i + 1) * 20
                    
            # 최종 결과
            async with self:
                self.result = f"비동기 작업 완료! 시간: {datetime.now().strftime('%H:%M:%S')}"
                self.is_loading = False
                
        except Exception as e:
            async with self:
                self.error_message = f"오류 발생: {str(e)}"
                self.is_loading = False


# 5. 상태 간 통신 테스트
class SettingsState(rx.State):
    """설정 상태"""
    theme: str = "light"
    language: str = "ko"
    
    @rx.event
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"


class MainState(rx.State):
    """메인 상태 - 다른 상태와 통신"""
    content: str = ""
    settings_info: str = ""
    
    @rx.event
    async def update_content_based_on_settings(self):
        """설정에 따라 콘텐츠 업데이트"""
        settings = await self.get_state(SettingsState)
        
        if settings.theme == "dark":
            self.content = "🌙 다크 모드 콘텐츠"
        else:
            self.content = "☀️ 라이트 모드 콘텐츠"
            
        self.settings_info = f"테마: {settings.theme}, 언어: {settings.language}"


# UI 컴포넌트들
def basic_state_test():
    """기본 상태 테스트 UI"""
    return rx.vstack(
        rx.heading("1. 기본 State 테스트", size="4"),
        rx.hstack(
            rx.text(f"카운트: {BasicState.count}"),
            rx.text(f"더블: {BasicState.double_count}"),
        ),
        rx.button("증가", on_click=BasicState.increment),
        rx.input(
            placeholder="이름 입력",
            on_change=BasicState.set_name,
            value=BasicState.name
        ),
        rx.text(f"입력된 이름: {BasicState.name}"),
        rx.cond(
            BasicState.has_items,
            rx.text("아이템이 있습니다"),
            rx.text("아이템이 없습니다")
        ),
        padding="1em",
        border="1px solid #ddd",
        margin="1em"
    )


def nan_handling_test():
    """NaN 처리 테스트 UI"""
    return rx.vstack(
        rx.heading("2. NaN 처리 테스트", size="4"),
        rx.button("NaN 데이터 처리 테스트", on_click=NaNHandlingState.test_nan_handling),
        rx.text(f"상관관계 요약: {NaNHandlingState.correlation_summary}"),
        rx.cond(
            NaNHandlingState.processed_data,
            rx.vstack(
                rx.text("처리된 데이터:"),
                rx.foreach(
                    NaNHandlingState.processed_data,
                    lambda item: rx.text(f"행 {item['index']}: A={item['A']:.1f}, B={item['B']:.1f}, C={item['C']:.1f}")
                )
            ),
            rx.text("처리된 데이터가 없습니다")
        ),
        padding="1em",
        border="1px solid #ddd",
        margin="1em"
    )


def list_rendering_test():
    """리스트 렌더링 테스트 UI"""
    return rx.vstack(
        rx.heading("3. 리스트 렌더링 테스트", size="4"),
        
        # 동적 리스트 (rx.foreach 사용)
        rx.text("동적 리스트 (올바른 방법):"),
        rx.foreach(
            ListRenderingState.dynamic_items,
            lambda item, idx: rx.hstack(
                rx.text(f"{idx + 1}. {item}"),
                rx.button("삭제", on_click=lambda: ListRenderingState.remove_item(idx), size="1")
            )
        ),
        
        # 아이템 추가 폼
        rx.form(
            rx.input(name="item", placeholder="새 아이템"),
            rx.button("추가", type="submit"),
            on_submit=ListRenderingState.add_dynamic_item,
            reset_on_submit=True
        ),
        
        # 정적 리스트 (Python for loop - 비교용)
        rx.text("정적 리스트 (비교용):"),
        rx.vstack(
            *[rx.text(f"• {item}") for item in ["정적1", "정적2", "정적3"]]
        ),
        
        # 복합 데이터 리스트
        rx.text("복합 데이터 리스트:"),
        rx.foreach(
            ListRenderingState.complex_items,
            lambda item, idx: rx.hstack(
                rx.text(f"{item['name']}: {item['value']}"),
                rx.badge(
                    "활성" if item["active"] else "비활성",
                    color_scheme="green" if item["active"] else "gray"
                ),
                rx.button(
                    "토글",
                    on_click=lambda: ListRenderingState.toggle_complex_item(idx),
                    size="1"
                )
            )
        ),
        
        padding="1em",
        border="1px solid #ddd",
        margin="1em"
    )


def async_test():
    """비동기 처리 테스트 UI"""
    return rx.vstack(
        rx.heading("4. 비동기 처리 테스트", size="4"),
        rx.button(
            "비동기 작업 시작",
            on_click=AsyncState.simulate_async_task,
            disabled=AsyncState.is_loading
        ),
        rx.cond(
            AsyncState.is_loading,
            rx.vstack(
                rx.spinner(),
                rx.progress(value=AsyncState.progress),
                rx.text(f"진행률: {AsyncState.progress}%")
            ),
            rx.cond(
                AsyncState.result != "",
                rx.text(f"✅ {AsyncState.result}", color="green"),
                rx.text("대기 중...")
            )
        ),
        rx.cond(
            AsyncState.error_message != "",
            rx.text(f"❌ {AsyncState.error_message}", color="red")
        ),
        padding="1em",
        border="1px solid #ddd",
        margin="1em"
    )


def cross_state_test():
    """상태 간 통신 테스트 UI"""
    return rx.vstack(
        rx.heading("5. 상태 간 통신 테스트", size="4"),
        rx.hstack(
            rx.text(f"현재 테마: {SettingsState.theme}"),
            rx.button("테마 변경", on_click=SettingsState.toggle_theme)
        ),
        rx.button(
            "설정 기반 콘텐츠 업데이트",
            on_click=MainState.update_content_based_on_settings
        ),
        rx.cond(
            MainState.content != "",
            rx.vstack(
                rx.text(MainState.content, font_size="1.2em"),
                rx.text(MainState.settings_info, color="gray")
            )
        ),
        padding="1em",
        border="1px solid #ddd",
        margin="1em"
    )


def test_app():
    """전체 테스트 앱"""
    return rx.vstack(
        rx.heading("🧪 Reflex 사용법 가이드 검증 테스트", size="6", text_align="center"),
        rx.text("REFLEX_USAGE_GUIDE.md의 패턴들을 실제로 테스트합니다", text_align="center"),
        
        basic_state_test(),
        nan_handling_test(),
        list_rendering_test(),
        async_test(),
        cross_state_test(),
        
        rx.divider(),
        rx.text("🎯 모든 테스트가 정상 작동하면 가이드가 올바르게 작성된 것입니다!", 
                color="green", font_weight="bold", text_align="center"),
        
        max_width="1200px",
        margin="0 auto",
        padding="2em"
    )


# Reflex 앱 설정
app = rx.App()
app.add_page(test_app, route="/")


if __name__ == "__main__":
    print("🧪 Reflex 가이드 검증 테스트 시작")
    print("브라우저에서 http://localhost:3000 을 열어 테스트하세요")
    app.run()