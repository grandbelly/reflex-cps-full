from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from ..db import q


def _calculate_dynamic_limit(window: str) -> int:
    """Calculate appropriate limit based on time window to optimize query performance."""
    wl = (window or "").strip().lower()
    if "minute" in wl and ("1 " in wl or "5 " in wl):
        return 1440  # 1 day worth of minutes
    elif "hour" in wl and ("12" in wl or "24" in wl):
        return 2880  # 2 days worth of 10-minute buckets
    elif "day" in wl:
        if "7" in wl:
            return 1008  # 7 days worth of hours
        elif "30" in wl:
            return 720   # 30 days worth of hours
    return 10000  # Default maximum


def _auto_view(window: str) -> str:
    """단순 정책 매핑:
    - 분 단위(window에 'minute' 포함) → 1분 뷰
    - 시간 단위(window에 'hour' 포함)  → 10분 뷰
    - 일/월 단위(window에 'day'/'month' 포함) → 1시간 뷰(기본), 필요 시 1일 뷰 사용
    """
    wl = (window or "").strip().lower()
    if "minute" in wl:
        return "public.influx_agg_1m"
    if "hour" in wl:
        return "public.influx_agg_10m"
    if ("month" in wl) or ("months" in wl) or ("day" in wl):
        # 기본은 1시간 집계. 1일 집계는 resolution='1d'로 강제 지정 시 사용
        return "public.influx_agg_1h"
    return "public.influx_agg_1h"


async def timeseries(
    window: str,
    tag_name: Optional[str],
    resolution: Optional[str] = None,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch timeseries with optional resolution override ('1m'|'10m'|'1h'|'1d').

    Returns all standard columns: n, avg, sum, min, max, last, first, diff.
    Ordered by time ascending for stable charting.
    """
    if resolution in {"1m", "1min", "1minute", "1 minute"}:
        view = "public.influx_agg_1m"
    elif resolution in {"10m", "10min", "10 minutes", "10 minute"}:
        view = "public.influx_agg_10m"
    elif resolution in {"1h", "1hour", "1 hour"}:
        view = "public.influx_agg_1h"
    elif resolution in {"1d", "1day", "1 day"}:
        view = "public.influx_agg_1d"
    else:
        view = _auto_view(window)

    if start_iso and end_iso:
        limit = _calculate_dynamic_limit(window or "7 days")
        sql = f"""
            SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
            FROM {view}
            WHERE bucket BETWEEN %s::timestamptz AND %s::timestamptz
              AND (%s::text IS NULL OR tag_name = %s)
            ORDER BY bucket ASC
            LIMIT {limit}
        """
        params_se: Tuple[Optional[str], Optional[str], Optional[str], Optional[str]] = (
            start_iso,
            end_iso,
            tag_name,
            tag_name,
        )
        return await q(sql, params_se)

    limit = _calculate_dynamic_limit(window)
    sql = f"""
        SELECT bucket, tag_name, n, avg, sum, min, max, last, first, diff
        FROM {view}
        WHERE bucket >= now() - %s::interval
          AND (%s::text IS NULL OR tag_name = %s)
        ORDER BY bucket ASC
        LIMIT {limit}
    """
    params: Tuple[str, Optional[str], Optional[str]] = (window, tag_name, tag_name)
    return await q(sql, params)


