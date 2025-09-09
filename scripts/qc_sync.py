from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict
import psycopg
from psycopg.types.json import Json


UPSERT_SQL = """
INSERT INTO public.influx_qc_rule as t
    (tag_name, min_val, max_val, max_step, max_gap_seconds, allow_negative, enabled, meta,
     warn_min, warn_max, crit_min, crit_max, roc_max_per_min, spike_zscore, deadband_pct)
VALUES
    (%(tag_name)s, %(min_val)s, %(max_val)s, %(max_step)s, %(max_gap_seconds)s, %(allow_negative)s, %(enabled)s, %(meta)s,
     %(warn_min)s, %(warn_max)s, %(crit_min)s, %(crit_max)s, %(roc_max_per_min)s, %(spike_zscore)s, %(deadband_pct)s)
ON CONFLICT (tag_name)
DO UPDATE SET
    min_val = EXCLUDED.min_val,
    max_val = EXCLUDED.max_val,
    max_step = EXCLUDED.max_step,
    max_gap_seconds = EXCLUDED.max_gap_seconds,
    allow_negative = EXCLUDED.allow_negative,
    enabled = EXCLUDED.enabled,
    meta = EXCLUDED.meta,
    warn_min = EXCLUDED.warn_min,
    warn_max = EXCLUDED.warn_max,
    crit_min = EXCLUDED.crit_min,
    crit_max = EXCLUDED.crit_max,
    roc_max_per_min = EXCLUDED.roc_max_per_min,
    spike_zscore = EXCLUDED.spike_zscore,
    deadband_pct = EXCLUDED.deadband_pct;
"""


def get_dsn() -> str:
    dsn = os.environ.get("TS_DSN")
    if not dsn:
        raise RuntimeError("TS_DSN is not set in environment")
    return dsn


def parse_bool(v: str | None) -> bool | None:
    if v is None or v == "":
        return None
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def parse_float(v: str | None) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def upsert_from_csv(csv_path: Path) -> int:
    dsn = get_dsn()
    rows: list[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({
                "tag_name": (row.get("tag_name") or "").strip(),
                "min_val": parse_float(row.get("min_val")),
                "max_val": parse_float(row.get("max_val")),
                "max_step": parse_float(row.get("max_step")),
                "max_gap_seconds": int(row.get("max_gap_seconds") or 0) if (row.get("max_gap_seconds") or "").strip() != "" else None,
                "allow_negative": parse_bool(row.get("allow_negative")),
                "enabled": parse_bool(row.get("enabled")),
                "meta": Json(json.loads(row.get("meta") or "{}")),
                "warn_min": parse_float(row.get("warn_min")),
                "warn_max": parse_float(row.get("warn_max")),
                "crit_min": parse_float(row.get("crit_min")),
                "crit_max": parse_float(row.get("crit_max")),
                "roc_max_per_min": parse_float(row.get("roc_max_per_min")),
                "spike_zscore": parse_float(row.get("spike_zscore")),
                "deadband_pct": parse_float(row.get("deadband_pct")),
            })

    applied = 0
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            # FK 보호: 존재하는 태그만 업서트
            cur.execute("SELECT tag_name FROM public.influx_tag")
            existing = {r[0] for r in cur.fetchall()}
            for row in rows:
                t = row.get("tag_name")
                if not t or t not in existing:
                    # skip unknown tags to avoid FK violation
                    continue
                cur.execute(UPSERT_SQL, row)
                applied += 1
    return applied


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "data/qc/influx_qc_rule.csv"
    if not src.exists():
        raise SystemExit(f"CSV not found: {src.as_posix()}")
    n = upsert_from_csv(src)
    print(f"Upserted {n} rows from {src.as_posix()}")


if __name__ == "__main__":
    main()


