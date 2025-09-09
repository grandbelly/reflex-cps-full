import reflex as rx
import os
from pathlib import Path

# Load environment variables from .env file
def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    print(f"🔍 Loading .env from: {env_path}")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value
                    print(f"✅ Loaded env var: {key}={'***' if 'password' in key.lower() or 'dsn' in key.lower() else value}")
    else:
        print(f"❌ .env file not found at {env_path}")
    
    # 중요한 환경변수 확인
    ts_dsn = os.getenv('TS_DSN')
    if ts_dsn:
        print("✅ TS_DSN is loaded successfully")
    else:
        print("❌ TS_DSN is not set!")

load_env()

# Refresh materialized view on app startup
import psycopg

def refresh_materialized_views():
    """Refresh materialized views on startup and periodically"""
    try:
        dsn = os.getenv('TS_DSN')
        if dsn:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    print("🔄 Refreshing materialized views...")
                    
                    # Refresh all technical indicator views
                    views_to_refresh = [
                        "tech_ind_1m_mv",
                        "tech_ind_10m_mv", 
                        "tech_ind_1h_mv",
                        "tech_ind_1d_mv"
                    ]
                    
                    for view in views_to_refresh:
                        try:
                            cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY public.{view}")
                            print(f"  ✅ Refreshed {view}")
                        except Exception as ve:
                            # Try without CONCURRENTLY if it fails
                            try:
                                cur.execute(f"REFRESH MATERIALIZED VIEW public.{view}")
                                print(f"  ✅ Refreshed {view} (non-concurrent)")
                            except:
                                print(f"  ⚠️ Failed to refresh {view}: {ve}")
                    
                    conn.commit()
                    print("✅ All materialized views refreshed successfully")
    except Exception as e:
        print(f"⚠️ Failed to refresh materialized views: {e}")

# Run refresh on startup
try:
    refresh_materialized_views()
except:
    pass  # Don't fail app startup if refresh fails

from .components.layout import shell, stat_card
from .components.kpi_tiles import unified_kpi_card
from .components.gauge import radial_gauge
# Demo import removed from UI (keep file for reference)
from .components.features_table import features_table
from .components.indicators_table import indicators_table
from .components.trend_enhanced import clean_area_chart, metric_card, time_range_pills, sensor_info_header
from .states.dashboard import DashboardState as D
from .pages.ai_insights import ai_insights_page
from .pages.communication import communication_page

# 보안 기능 추가 (충돌 해결)
try:
    from .security import validate_startup_security, get_csp_headers
    # 애플리케이션 시작시 보안 검증
    validate_startup_security()
except ImportError:
    # 보안 모듈이 없으면 경고만 출력
    logging.warning("⚠️ 보안 모듈을 찾을 수 없습니다. 보안 검증을 건너뜁니다.")
except Exception as e:
    logging.error(f"🚨 보안 검증 실패: {e}", exc_info=True)
    # 개발환경에서는 계속 진행, 운영환경에서는 중단 고려


# Gradient creation function from dashboard template
def _create_gradient(color: str, id: str) -> rx.Component:
    return (
        rx.el.svg.defs(
            rx.el.svg.linear_gradient(
                rx.el.svg.stop(
                    stop_color=color, offset="5%", stop_opacity=0.8
                ),
                rx.el.svg.stop(
                    stop_color=color, offset="95%", stop_opacity=0
                ),
                x1=0,
                x2=0,
                y1=0,
                y2=1,
                id=id,
            ),
        ),
    )




# Chart toggle buttons (like dashboard template)
# 상위 토글: Area/Composed 전환 (대시보드 템플릿 스타일)
def main_chart_toggle_button() -> rx.Component:
    """차트 뷰 모드 토글 - 전환 대상 모드 아이콘을 표시"""
    return rx.cond(
        D.chart_view_mode,
        # Area 모드일 때 → Composed 모드로 전환 (layers 아이콘 표시)
        rx.icon_button(
            rx.icon("layers"),
            size="2",
            cursor="pointer",
            variant="surface",
            on_click=D.toggle_chart_view_mode,
        ),
        # Composed 모드일 때 → Area 모드로 전환 (area-chart 아이콘 표시)
        rx.icon_button(
            rx.icon("area-chart"),
            size="2",
            cursor="pointer", 
            variant="surface",
            on_click=D.toggle_chart_view_mode,
        ),
    )


# 재사용 가능한 토글 그룹 컴포넌트
def create_toggle_group(items: list, value: rx.Var, on_change, multiple: bool = False) -> rx.Component:
    """통일된 토글 그룹 컴포넌트"""
    control_items = [rx.segmented_control.item(item["label"], value=item["value"]) for item in items]
    
    control_props = {
        "value": value,
        "on_change": on_change,
        "size": "2",
    }
    
    if multiple:
        control_props["type"] = "multiple"
    
    return rx.flex(
        rx.segmented_control.root(*control_items, **control_props),
        gap="3", align="center",
    )


def create_checkbox_group(items: list, selected: rx.Var, on_change) -> rx.Component:
    """Checkbox group for multiple selection"""
    def make_checkbox(item: dict) -> rx.Component:
        return rx.checkbox(
            item["label"],
            checked=selected.contains(item["value"]),
            on_change=lambda checked: on_change(item["value"], checked),
            size="2",
            color_scheme="blue",
        )
    
    return rx.flex(
        *[make_checkbox(item) for item in items],
        gap="3",
        wrap="wrap",
        align="center",
    )


# Area 모드 - Trend 그룹 토글 버튼들 (Segmented Control)
def trend_toggle_group() -> rx.Component:
    trend_items = [
        {"label": "Avg", "value": "avg"},
        {"label": "Min", "value": "min"},
        {"label": "Max", "value": "max"},
        {"label": "First", "value": "first"},
        {"label": "Last", "value": "last"},
    ]
    return create_toggle_group(trend_items, D.trend_selected, D.set_trend_selected)


# Area 모드 - Tech 그룹 토글 버튼들 (Segmented Control)
def tech_toggle_group() -> rx.Component:
    tech_items = [
        {"label": "Avg", "value": "avg"},
        {"label": "SMA10", "value": "sma_10"},
        {"label": "SMA60", "value": "sma_60"},
        {"label": "BB Upper", "value": "bb_upper"},
        {"label": "BB Lower", "value": "bb_lower"},
    ]
    return create_toggle_group(tech_items, D.tech_selected, D.set_tech_selected)


# Composed 모드 - Trend 체크박스 그룹 (다중 선택)
def trend_composed_checkboxes() -> rx.Component:
    trend_items = [
        {"label": "Min", "value": "min"},
        {"label": "Max", "value": "max"},
        {"label": "First", "value": "first"},
        {"label": "Last", "value": "last"},
    ]
    return create_checkbox_group(trend_items, D.trend_composed_selected, D.toggle_trend_composed_item)


# Composed 모드 - Tech 체크박스 그룹 (다중 선택)
def tech_composed_checkboxes() -> rx.Component:
    # Main chart indicators only (Bollinger Bands are always shown in auxiliary chart)
    tech_items = [
        {"label": "SMA10", "value": "sma_10"},
        {"label": "SMA60", "value": "sma_60"},
    ]
    return create_checkbox_group(tech_items, D.tech_composed_selected, D.toggle_tech_composed_item)


# 새로운 컴포즈드 차트: 세그먼트 컨트롤 연동
def trend_composed_chart_new() -> rx.Component:
    """Trend Composed Chart with unified style"""
    return rx.recharts.composed_chart(
        rx.recharts.cartesian_grid(stroke_dasharray="3 3", opacity=0.1),
        rx.recharts.legend(vertical_align="top", height=30),
        rx.recharts.graphing_tooltip(),
        # Base average as bars (always shown)
        rx.recharts.bar(
            data_key="avg",
            fill="#10b981",
            opacity=0.3,
            name="Average"
        ),
        # Trend indicators with dashed lines
        rx.cond(
            D.show_trend_min,
            rx.recharts.line(
                data_key="min", 
                stroke="#60a5fa", 
                stroke_width=2, 
                stroke_dasharray="5 5",
                dot=False, 
                type_="monotone", 
                name="Min"
            ),
            rx.fragment()
        ),
        rx.cond(
            D.show_trend_max,
            rx.recharts.line(
                data_key="max", 
                stroke="#f97316", 
                stroke_width=2, 
                stroke_dasharray="8 4",
                dot=False, 
                type_="monotone", 
                name="Max"
            ),
            rx.fragment()
        ),
        rx.cond(
            D.show_trend_first,
            rx.recharts.line(
                data_key="first", 
                stroke="#22d3ee", 
                stroke_width=2, 
                stroke_dasharray="10 5", 
                dot=False, 
                type_="monotone", 
                name="First"
            ),
            rx.fragment()
        ),
        rx.cond(
            D.show_trend_last,
            rx.recharts.line(
                data_key="last", 
                stroke="#a78bfa", 
                stroke_width=2, 
                stroke_dasharray="12 3",
                dot=False, 
                type_="monotone", 
                name="Last"
            ),
            rx.fragment()
        ),
        rx.recharts.x_axis(data_key="bucket_formatted", stroke="#64748b", tick_line=False, axis_line=False, tick={"fontSize": "10px", "angle": -45, "textAnchor": "end"}, height=80, interval="preserveStartEnd"),
        rx.recharts.y_axis(domain=["auto","auto"], allow_decimals=True, stroke="#64748b", tick={"fontSize": "12px"}),
        data=D.series_for_tag,
        margin={"top": 50, "right": 30, "left": 20, "bottom": 100},
        height=500,
    )


def tech_composed_chart_new() -> rx.Component:
    """Stock-style dual chart layout with main and auxiliary indicators"""
    return rx.cond(
        D.indicators_for_tag.length() > 0,
        rx.vstack(
        # Main Chart (Price with SMA indicators)
        rx.box(
            rx.text("Main Indicators", class_name="text-xs text-gray-500 mb-2"),
            rx.recharts.composed_chart(
                rx.recharts.cartesian_grid(stroke_dasharray="3 3", opacity=0.1),
                rx.recharts.legend(vertical_align="top", height=24),
                rx.recharts.graphing_tooltip(),
                # Base average as bars (always shown)
                rx.recharts.bar(
                    data_key="avg",
                    fill="#10b981",
                    opacity=0.3,
                    name="Average",
                ),
                # SMA indicators with dashed lines
                rx.cond(
                    D.show_tech_sma_10,
                    rx.recharts.line(
                        data_key="sma_10", 
                        stroke="#8b5cf6", 
                        stroke_width=2, 
                        stroke_dasharray="5 5",
                        dot=False, 
                        type_="monotone", 
                        name="SMA 10"
                    ),
                    rx.fragment()
                ),
                rx.cond(
                    D.show_tech_sma_60,
                    rx.recharts.line(
                        data_key="sma_60", 
                        stroke="#f59e0b", 
                        stroke_width=2, 
                        stroke_dasharray="8 4",
                        dot=False, 
                        type_="monotone", 
                        name="SMA 60"
                    ),
                    rx.fragment()
                ),
                rx.recharts.x_axis(
                    data_key="bucket_formatted", 
                    hide=True  # Hide X-axis on main chart
                ),
                rx.recharts.y_axis(
                    domain=["auto", "auto"],
                    allow_decimals=True, 
                    stroke="#64748b", 
                    tick={"fontSize": "11px"},
                    width=70,
                    padding={"top": 20, "bottom": 20}
                ),
                data=D.indicators_for_tag,
                margin={"top": 20, "right": 30, "left": 60, "bottom": 0},
                height=350,
                width="100%",
                style={"width": "100%"},
            ),
            class_name="w-full"
        ),
        # Auxiliary Chart (Bollinger Bands)
        rx.box(
            rx.text("Auxiliary Indicators", class_name="text-xs text-gray-500 mb-1"),
            rx.recharts.composed_chart(
                rx.recharts.cartesian_grid(stroke_dasharray="3 3", opacity=0.1),
                rx.recharts.legend(vertical_align="top", height=24),
                rx.recharts.graphing_tooltip(),
                # Average line as solid line
                rx.recharts.line(
                    data_key="avg",
                    stroke="#3b82f6",
                    stroke_width=2,
                    dot=False,
                    type_="monotone",
                    name="Average"
                ),
                # Bollinger Upper Band with dashed line
                rx.recharts.line(
                    data_key="bb_top", 
                    stroke="#ef4444", 
                    stroke_width=2, 
                    dot=False, 
                    stroke_dasharray="8 4", 
                    type_="monotone", 
                    name="BB Upper"
                ),
                # Bollinger Lower Band with dashed line
                rx.recharts.line(
                    data_key="bb_bot", 
                    stroke="#22c55e", 
                    stroke_width=2, 
                    dot=False, 
                    stroke_dasharray="8 4", 
                    type_="monotone", 
                    name="BB Lower"
                ),
                rx.recharts.x_axis(
                    data_key="bucket_formatted", 
                    stroke="#64748b", 
                    tick_line=False, 
                    axis_line=False, 
                    tick={"fontSize": "10px", "angle": -45, "textAnchor": "end"}, 
                    height=60, 
                    interval="preserveStartEnd"
                ),
                rx.recharts.y_axis(
                    domain=["auto", "auto"],
                    allow_decimals=True, 
                    stroke="#64748b", 
                    tick={"fontSize": "11px"},
                    width=70,
                    padding={"top": 20, "bottom": 20}
                ),
                data=D.indicators_for_tag,
                margin={"top": 10, "right": 30, "left": 60, "bottom": 60},
                height=280,
                width="100%",
                style={"width": "100%"},
            ),
            class_name="w-full border-t border-gray-200 pt-2"
        ),
        spacing="2",
        width="100%",
        class_name="w-full bg-white dark:bg-gray-800 p-4 rounded-lg"
    ),
    rx.box()  # Empty placeholder when no data
    )






def index() -> rx.Component:
    """메인 대시보드 페이지 - 예전 스타일로 복원"""
    return rx.fragment(
        # 페이지 로드 시 데이터 자동 로딩
        rx.script("console.log('페이지 로드됨, 데이터 로딩 시작')"),
        shell( 
            rx.vstack(
                
                # 로딩/에러 상태 표시 (디버깅 정보 포함)
                rx.cond(
                    D.loading,
                    rx.center(
                        rx.vstack(
                            rx.spinner(size="3"),
                            rx.text("데이터 로딩 중...", class_name="text-gray-600"),
                            rx.text(f"실시간 모드: {D.realtime_mode}", class_name="text-xs text-gray-400"),
                            rx.text(f"로딩 상태: {D.loading}", class_name="text-xs text-gray-400"),
                            spacing="3",
                            align="center"
                        ),
                        height="400px"
                    ),
                    rx.cond(
                        D.error,
                        rx.center(
                            rx.vstack(
                                rx.icon("circle-alert", size=48, color="red"),
                                rx.text(f"에러: {D.error}", class_name="text-red-600"),
                                rx.button("다시 시도", on_click=D.reload, color_scheme="red"),
                                spacing="3",
                                align="center"
                            ),
                            height="400px"
                        ),
                        # 센서 카드 그리드 (예전 스타일)
                        rx.cond(
                            D.kpi_rows,
                            rx.box(
                                rx.foreach(
                                    D.kpi_rows,
                                    lambda r: unified_kpi_card(
                                        r["tag_name"],
                                        r["value_s"],
                                        r["delta_pct"],
                                        r["delta_s"],
                                        r["status_level"],
                                        r["ts_s"],
                                        r["range_label"],
                                        chart_data=r.get("mini_chart_data", []),
                                        gauge_pct=r.get("gauge_pct", 0),
                                        comm_status=r.get("comm_status"),
                                        comm_text=r.get("comm_text"),
                                        realtime_mode=D.realtime_mode,
                                        realtime_data=r.get("realtime_chart_data", []),
                                        qc_min=r.get("qc_min"),
                                        qc_max=r.get("qc_max"),
                                        on_detail_click=lambda tag=r["tag_name"]: D.open_detail_modal(tag),
                                        unit=r.get("unit", ""),
                                    )
                                ),
                                display="grid",
                                grid_template_columns="repeat(auto-fit, minmax(300px, 1fr))",
                                gap="4",
                                padding="4",
                                width="100%"
                            ),
                            # 데이터가 없는 경우 (디버깅 정보 포함)
                            rx.center(
                                rx.vstack(
                                    rx.icon("database", size=48, color="gray"),
                                    rx.text("센서 데이터가 없습니다", class_name="text-gray-600"),
                                    rx.text("KPI rows: 로딩 중...", class_name="text-xs text-gray-400"),
                                    rx.text("Tags: 로딩 중...", class_name="text-xs text-gray-400"), 
                                    rx.text("Latest: 로딩 중...", class_name="text-xs text-gray-400"),
                                    rx.text(f"Error: {D.error}", class_name="text-xs text-red-400"),
                                    rx.button("새로고침", on_click=D.reload, color_scheme="blue"),
                                    spacing="3",
                                    align="center"
                                ),
                                height="400px"
                            )
                        )
                    )
                ),
                
                spacing="0",
                width="100%"
            ),
            # 메인 대시보드에서만 데이터 로드 및 실시간 모드 시작
            on_mount=D.load
        )
    )


app = rx.App(theme=rx.theme(appearance="light"), stylesheets=["/styles.css"])
app.add_page(index, route="/")

# Trend page (moved controls + series chart + measurement table)
def trend_page() -> rx.Component:
    return shell(
        rx.vstack(
            
            # Controls - Enhanced design
            rx.card(
                rx.flex(
                    rx.flex(
                        rx.icon("tag", size=16, color="gray"),
                        rx.text("태그 선택", size="2", weight="medium", color="gray"),
                        spacing="2",
                        align="center"
                    ),
                    rx.el.select(
                        rx.foreach(D.tags, lambda t: rx.el.option(t, value=t)),
                        value=rx.cond(D.tag_name, D.tag_name, ""),
                        on_change=[D.set_tag_select, D.load],
                        class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-blue-200 w-56 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm",
                    ),
                    rx.flex(
                        rx.icon("clock", size=16, color="gray"),
                        rx.text("조회기간", size="2", weight="medium", color="gray"),
                        spacing="2",
                        align="center"
                    ),
                    rx.el.select(
                        rx.el.option("5분", value="5 min"),
                        rx.el.option("1시간", value="60 min"),
                        rx.el.option("24시간", value="24 hour"),
                        rx.el.option("7일", value="7 days"),
                        rx.el.option("30일", value="30 days"),
                        rx.el.option("3개월", value="3 months"),
                        rx.el.option("1년", value="12 months"),
                        value=D.window,
                        on_change=[D.set_window, D.load],
                        class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-blue-200 w-32 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm",
                    ),
                    spacing="4",
                    align="center"
                ),
                class_name="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 shadow-md"
            ),
            
            # Series chart - Full-width responsive card
            rx.card(
                rx.flex(
                    rx.heading(rx.cond(D.tag_name, D.tag_name, "Time Series"), size="4", weight="bold"),
                    rx.spacer(),
                    rx.flex(
                        # Area 모드일 때: 토글 버튼 그룹
                        rx.cond(
                            D.chart_view_mode,
                            trend_toggle_group(),
                            rx.fragment(),
                        ),
                        # Composed 모드일 때: 체크박스만 표시 (레거시 토글 제거)
                        rx.cond(
                            D.chart_view_mode,
                            rx.fragment(),
                            trend_composed_checkboxes(),
                        ),
                        main_chart_toggle_button(),
                        gap="4", align="center",
                    ),
                    align="center", 
                    class_name="mb-4",
                ),
                
                rx.cond(
                    D.series_for_tag,
                    rx.cond(
                        D.chart_view_mode,
                        # Area 모드: 선택된 계열만 gradient area 차트로 표시
                        rx.cond(
                            D.trend_selected == "avg",
                            rx.recharts.area_chart(
                                _create_gradient("#10b981", "avgGradient"),
                                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                rx.recharts.area(
                                    data_key="avg",
                                    stroke="#10b981",
                                    fill="url(#avgGradient)",
                                    type_="monotone",
                                    name="Average"
                                ),
                                rx.recharts.x_axis(data_key="bucket_formatted"),
                                rx.recharts.y_axis(),
                                rx.recharts.tooltip(),
                                rx.recharts.legend(),
                                data=D.series_for_tag,
                                height=500,
                            ),
                            rx.cond(
                                D.trend_selected == "min",
                                rx.recharts.area_chart(
                                    _create_gradient("#60a5fa", "minGradient"),
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                    rx.recharts.area(
                                        data_key="min",
                                        stroke="#60a5fa",
                                        fill="url(#minGradient)",
                                        type_="monotone",
                                        name="Minimum"
                                    ),
                                    rx.recharts.x_axis(data_key="bucket_formatted"),
                                    rx.recharts.y_axis(),
                                    rx.recharts.tooltip(),
                                    rx.recharts.legend(),
                                    data=D.series_for_tag,
                                    height=500,
                                ),
                                rx.cond(
                                    D.trend_selected == "max",
                                    rx.recharts.area_chart(
                                        _create_gradient("#f97316", "maxGradient"),
                                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                        rx.recharts.area(
                                            data_key="max",
                                            stroke="#f97316",
                                            fill="url(#maxGradient)",
                                            type_="monotone",
                                            name="Maximum"
                                        ),
                                        rx.recharts.x_axis(data_key="bucket_formatted"),
                                        rx.recharts.y_axis(),
                                        rx.recharts.tooltip(),
                                        rx.recharts.legend(),
                                        data=D.series_for_tag,
                                        height=500,
                                    ),
                                    rx.cond(
                                        D.trend_selected == "first",
                                        rx.recharts.area_chart(
                                            _create_gradient("#22d3ee", "firstGradient"),
                                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                            rx.recharts.area(
                                                data_key="first",
                                                stroke="#22d3ee",
                                                fill="url(#firstGradient)",
                                                type_="monotone",
                                                name="First"
                                            ),
                                            rx.recharts.x_axis(data_key="bucket_formatted"),
                                            rx.recharts.y_axis(),
                                            rx.recharts.tooltip(),
                                            rx.recharts.legend(),
                                            data=D.series_for_tag,
                                            height=500,
                                        ),
                                        # trend_selected == "last"
                                        rx.recharts.area_chart(
                                            _create_gradient("#a78bfa", "lastGradient"),
                                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                            rx.recharts.area(
                                                data_key="last",
                                                stroke="#a78bfa",
                                                fill="url(#lastGradient)",
                                                type_="monotone",
                                                name="Last"
                                            ),
                                            rx.recharts.x_axis(data_key="bucket_formatted"),
                                            rx.recharts.y_axis(),
                                            rx.recharts.tooltip(),
                                            rx.recharts.legend(),
                                            data=D.series_for_tag,
                                            height=500,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        # Composed 모드: 새로운 방식 (세그먼트 컨트롤 연동 차트)
                        trend_composed_chart_new(),
                    ),
                    rx.flex(
                        rx.icon("line-chart", size=48, color="gray"),
                        rx.text("No chart data available", size="3", color="gray"),
                        rx.text("Adjust filters and reload", size="2", color="gray"),
                        direction="column",
                        align="center",
                        gap="2",
                        class_name="py-16",
                    ),
                ),
                class_name="w-full min-h-[500px]",
            ),
            
            # Measurement table - Full-width responsive
            features_table(),
            
            spacing="4",
            width="100%",
            class_name="p-4"
        ),
        # 트렌드 페이지 - 데이터 로딩 없음 (메인에서 관리)
        active_route="/trend",
    )

app.add_page(trend_page, route="/trend")
# Tech Indicator page
def tech_page() -> rx.Component:
    return shell(
        rx.vstack(
            
            # Controls - Enhanced design 
            rx.card(
                rx.flex(
                    rx.flex(
                        rx.icon("tag", size=16, color="gray"),
                        rx.text("태그 선택", size="2", weight="medium", color="gray"),
                        spacing="2",
                        align="center"
                    ),
                    rx.el.select(
                        rx.foreach(D.tags, lambda t: rx.el.option(t, value=t)),
                        value=rx.cond(D.tag_name, D.tag_name, ""),
                        on_change=[D.set_tag_select, D.load],
                        class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-purple-200 w-56 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm",
                    ),
                    rx.flex(
                        rx.icon("clock", size=16, color="gray"),
                        rx.text("조회기간", size="2", weight="medium", color="gray"),
                        spacing="2",
                        align="center"
                    ),
                    rx.el.select(
                        rx.el.option("5분", value="5 min"),
                        rx.el.option("1시간", value="60 min"),
                        rx.el.option("24시간", value="24 hour"),
                        rx.el.option("7일", value="7 days"),
                        rx.el.option("30일", value="30 days"),
                        rx.el.option("3개월", value="3 months"),
                        rx.el.option("1년", value="12 months"),
                        value=D.window,
                        on_change=[D.set_window, D.load],
                        class_name="bg-white text-gray-900 px-3 py-2 rounded-lg border-2 border-purple-200 w-32 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm",
                    ),
                    spacing="4",
                    align="center"
                ),
                class_name="mb-4 bg-gradient-to-r from-purple-50 to-indigo-50 border-2 border-purple-200 shadow-md"
            ),
            
            # Indicators chart - Modern card design with dual-mode controls
            rx.card(
                rx.flex(
                    rx.heading(rx.cond(D.tag_name, D.tag_name, "Technical Indicators"), size="4", weight="bold"),
                    rx.spacer(),
                    rx.flex(
                        # Area 모드일 때: 테크 토글 버튼 그룹
                        rx.cond(
                            D.chart_view_mode,
                            tech_toggle_group(),
                            rx.fragment(),
                        ),
                        # Composed 모드일 때: 테크 체크박스만 표시
                        rx.cond(
                            D.chart_view_mode,
                            rx.fragment(),
                            tech_composed_checkboxes(),
                        ),
                        main_chart_toggle_button(),
                        gap="4", align="center",
                    ),
                    align="center",
                    class_name="mb-4",
                ),
                
                rx.cond(
                    D.indicators_for_tag,
                    rx.cond(
                        D.chart_view_mode,
                        # Area 모드: 선택된 tech indicator만 gradient area 차트로 표시
                        rx.cond(
                            D.tech_selected == "avg",
                            rx.recharts.area_chart(
                                _create_gradient("#3b82f6", "avgTechGradient"),
                                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                rx.recharts.area(
                                    data_key="avg",
                                    stroke="#3b82f6",
                                    fill="url(#avgTechGradient)",
                                    type_="monotone",
                                    name="Average"
                                ),
                                rx.recharts.x_axis(data_key="bucket_formatted"),
                                rx.recharts.y_axis(),
                                rx.recharts.tooltip(),
                                rx.recharts.legend(),
                                data=D.indicators_for_tag,
                                height=500,
                            ),
                            rx.cond(
                                D.tech_selected == "sma_10",
                                rx.recharts.area_chart(
                                    _create_gradient("#8b5cf6", "sma10TechGradient"),
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                    rx.recharts.area(
                                        data_key="sma_10",
                                        stroke="#8b5cf6",
                                        fill="url(#sma10TechGradient)",
                                        type_="monotone",
                                        name="SMA 10"
                                    ),
                                    rx.recharts.x_axis(data_key="bucket_formatted"),
                                    rx.recharts.y_axis(),
                                    rx.recharts.tooltip(),
                                    rx.recharts.legend(),
                                    data=D.indicators_for_tag,
                                    height=500,
                                ),
                                rx.cond(
                                    D.tech_selected == "sma_60",
                                    rx.recharts.area_chart(
                                        _create_gradient("#f59e0b", "sma60TechGradient"),
                                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                        rx.recharts.area(
                                            data_key="sma_60",
                                            stroke="#f59e0b",
                                            fill="url(#sma60TechGradient)",
                                            type_="monotone",
                                            name="SMA 60"
                                        ),
                                        rx.recharts.x_axis(data_key="bucket_formatted"),
                                        rx.recharts.y_axis(),
                                        rx.recharts.tooltip(),
                                        rx.recharts.legend(),
                                        data=D.indicators_for_tag,
                                        height=500,
                                    ),
                                    rx.cond(
                                        D.tech_selected == "bb_upper",
                                        rx.recharts.area_chart(
                                            _create_gradient("#ef4444", "bbUpperTechGradient"),
                                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                            rx.recharts.area(
                                                data_key="bb_top",
                                                stroke="#ef4444",
                                                fill="url(#bbUpperTechGradient)",
                                                type_="monotone",
                                                name="BB Upper"
                                            ),
                                            rx.recharts.x_axis(data_key="bucket_formatted"),
                                            rx.recharts.y_axis(),
                                            rx.recharts.tooltip(),
                                            rx.recharts.legend(),
                                            data=D.indicators_for_tag,
                                            height=500,
                                        ),
                                        # tech_selected == "bb_lower"
                                        rx.recharts.area_chart(
                                            _create_gradient("#22c55e", "bbLowerTechGradient"),
                                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                            rx.recharts.area(
                                                data_key="bb_bot",
                                                stroke="#22c55e",
                                                fill="url(#bbLowerTechGradient)",
                                                type_="monotone",
                                                name="BB Lower"
                                            ),
                                            rx.recharts.x_axis(data_key="bucket_formatted"),
                                            rx.recharts.y_axis(),
                                            rx.recharts.tooltip(),
                                            rx.recharts.legend(),
                                            data=D.indicators_for_tag,
                                            height=500,
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        # Composed 모드: 새로운 방식 (세그먼트 컨트롤 연동 차트)
                        tech_composed_chart_new(),
                    ),
                    rx.flex(
                        rx.icon("trending-up", size=48, color="gray"),
                        rx.text("No indicators data available", size="3", color="gray"),
                        rx.text("Select a tag and time range", size="2", color="gray"),
                        direction="column",
                        align="center",
                        gap="2",
                        class_name="py-16",
                    ),
                ),
                class_name="w-full min-h-[500px]",
            ),
            
            # Indicators table - Full-width responsive  
            indicators_table(),
            
            spacing="4",
            width="100%",
            class_name="p-4"
        ),
        # 트렌드 페이지 - 데이터 로딩 없음 (메인에서 관리)
        active_route="/tech",
    )

app.add_page(tech_page, route="/tech")
app.add_page(ai_insights_page, route="/ai")  # AI Chat interface
app.add_page(communication_page, route="/comm")

# Real-time monitoring page
