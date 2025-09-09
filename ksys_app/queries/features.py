from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..db import q
from ..utils.query_optimizer import optimize_query_params


async def features_5m(window: str, tag_name: str | None) -> List[Dict[str, Any]]:
    # 🚀 성능 최적화: 동적 LIMIT 계산
    limit, hint = optimize_query_params(window, tag_name)
    
    sql = (
        "SELECT bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m "
        "FROM public.features_5m "
        "WHERE bucket >= now() - %s::interval "
        "  AND (%s::text IS NULL OR tag_name = %s) "
        "ORDER BY bucket "
        f"LIMIT {limit}"  # 동적 LIMIT 적용
    )
    params: Tuple[str, str | None, str | None] = (window, tag_name, tag_name)
    return await q(sql, params)


