import reflex as rx
import os

# Import DashboardState for sidebar toggle functionality  
from ..states.dashboard import DashboardState as D

# 앱 버전 가져오기 (FULL 또는 PART)
APP_VERSION = os.getenv("APP_VERSION", "FULL").upper()

# 버전별 메뉴 구성 정의
MENU_CONFIG = {
    "FULL": [
        {"icon": "bar-chart", "name": "Dashboard", "path": "/", "desc": "실시간 모니터링"},
        {"icon": "trending-up", "name": "Trends", "path": "/trend", "desc": "시계열 분석"},
        {"icon": "settings", "name": "Indicators", "path": "/tech", "desc": "기술지표"},
        {"icon": "signal", "name": "Comms", "path": "/comm", "desc": "통신 성공률"},
        {"icon": "bot", "name": "AI Insights", "path": "/ai", "desc": "AI 분석"},
    ],
    "PART": [
        {"icon": "bar-chart", "name": "Dashboard", "path": "/", "desc": "실시간 모니터링"},
        {"icon": "trending-up", "name": "Trends", "path": "/trend", "desc": "시계열 분석"},
        {"icon": "settings", "name": "Indicators", "path": "/tech", "desc": "기술지표"},
    ]
}

# 현재 버전의 메뉴 가져오기
ACTIVE_MENU = MENU_CONFIG.get(APP_VERSION, MENU_CONFIG["FULL"])


def collapsed_sidebar() -> rx.Component:
    """접힌 사이드바 (아이콘만 표시)"""
    return rx.card(
        # 토글 버튼 (펼치기)
        rx.flex(
            rx.button(
                rx.icon("panel-left-open", size=20),
                variant="ghost",
                size="2",
                class_name="hover:bg-gray-100 rounded-lg p-2",
                on_click=D.toggle_sidebar,
            ),
            direction="column",
            align="center",
            gap="4",
            class_name="pb-4 border-b border-gray-200",
        ),
        # 축소된 네비게이션 아이콘들 (동적 메뉴)
        rx.vstack(
            *[
                rx.button(
                    rx.icon(menu["icon"], size=18),
                    variant="ghost",
                    size="3", 
                    class_name="w-full hover:bg-blue-50",
                    on_click=lambda path=menu["path"]: rx.redirect(path),
                )
                for menu in ACTIVE_MENU
            ],
            spacing="2",
            align="stretch",
            class_name="pt-4",
        ),
        height="100vh",
        width="4rem", 
        class_name="hidden lg:flex flex-col border-r border-gray-200 bg-white shadow-lg sticky top-0",
    )


def sidebar(active: str = "/") -> rx.Component:
    return rx.card(
        # 상단 토글 버튼과 로고 섹션
        rx.flex(
            rx.flex(
                rx.button(
                    rx.icon("panel-left-close", size=20),
                    variant="ghost",
                    size="2",
                    class_name="hover:bg-gray-100 rounded-lg p-2",
                    on_click=D.toggle_sidebar,
                ),
                rx.image(
                    src="/logo.png",
                    alt="Ksys Logo",
                    height="2.5rem",
                    width="auto",
                ),
                align="center",
                gap="3",
            ),
            direction="column",
            align="center",
            gap="3",
            class_name="pb-4 border-b border-gray-200",
        ),
        
        # 네비게이션 메뉴 (동적 메뉴)
        rx.vstack(
            *[
                rx.link(
                    rx.flex(
                        rx.icon(menu["icon"], size=20, color=("gray.300" if active == menu["path"] else "black")),
                        rx.text(menu["name"], size="3", weight=("bold" if active == menu["path"] else "medium"), color=("gray.300" if active == menu["path"] else "black")),
                        align="center",
                        gap="3",
                    ),
                    href=menu["path"],
                    class_name=("w-full p-3 rounded-lg bg-black shadow-lg border-l-4 border-gray-800 transform scale-105" if active == menu["path"] 
                               else "w-full p-3 rounded-lg transition-all duration-200 hover:bg-gray-100 hover:text-black hover:shadow-md text-black"),
                )
                for menu in ACTIVE_MENU
            ],
            spacing="2",
            align="stretch",
            class_name="pt-6",
        ),
        
        height="100vh",
        width="16rem",
        class_name="hidden lg:flex flex-col border-r border-gray-200 bg-white shadow-lg sticky top-0",
    )


def top_nav_cards(active: str = "/") -> rx.Component:
    """최상단 헤더의 네비게이션 카드들 (동적 메뉴)"""
    return rx.flex(
        *[
            rx.link(
                rx.card(
                    rx.flex(
                        rx.icon(menu["icon"], size=(22 if active == menu["path"] else 18), color=("black" if active == menu["path"] else "gray")),
                        rx.vstack(
                            rx.text(menu["name"], size=("4" if active == menu["path"] else "2"), weight=("bold" if active == menu["path"] else "medium"), color="black"),
                            rx.text(menu["desc"], size="1", color="gray"),
                            spacing="0",
                            align="start"
                        ),
                        align="center",
                        gap="2"
                    ),
                    class_name="bg-white hover:bg-gray-50 hover:border-gray-300 border border-gray-200 transition-all duration-200 hover:shadow-md",
                    padding="3",
                    style={"min_width": "140px", "cursor": "pointer"}
                ),
                href=menu["path"],
                underline="none"
            )
            for menu in ACTIVE_MENU
        ],
        gap="3",
        align="center"
    )


def header(active_route: str = "/") -> rx.Component:
    return rx.el.header(
        # 네비게이션 카드들만 표시
        rx.flex(
            top_nav_cards(active_route),
            justify="center",
            class_name="py-4"
        ),
        class_name="w-full border-b border-gray-200 bg-white px-6 py-2 sticky top-0 z-10 shadow-sm",
    )


def stat_card(title: str, value: rx.Var | str, delta: str | None = None, good: bool | None = None, subtitle: str | None = None) -> rx.Component:
    badge = None
    if delta is not None and good is not None:
        badge = rx.el.span(
            delta,
            class_name=(
                "ml-2 text-xs px-1.5 py-0.5 rounded-md "
                + ("bg-green-50 text-green-700" if good else "bg-red-50 text-red-700")
            ),
        )
    return rx.el.div(
        rx.el.span(title, class_name="text-xs font-medium text-gray-500"),
        rx.el.div(
            rx.el.span(value, class_name="text-2xl font-semibold text-gray-900"),
            badge or rx.fragment(),
            class_name="flex items-center mt-1",
        ),
        rx.el.span(subtitle or "", class_name="text-xs text-gray-500 mt-1"),
        class_name="bg-white border border-gray-200 rounded-xl shadow-sm p-5"
    )


def shell(*children: rx.Component, on_mount=None, active_route: str = "/") -> rx.Component:
    return rx.el.div(
        # 조건부 사이드바 표시
        rx.cond(
            D.sidebar_collapsed,
            collapsed_sidebar(),
            sidebar(active_route)
        ),
        rx.el.div(
            header(active_route),
            rx.el.div(
                *children,
                class_name="w-full min-h-screen",
            ),
            class_name="flex-1 min-h-screen bg-white",
        ),
        class_name="w-full min-h-screen bg-white flex",
        on_mount=on_mount,
    )


