from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row


def get_dsn() -> str:
    dsn = os.environ.get("TS_DSN")
    if not dsn:
        raise RuntimeError("TS_DSN is not set in environment")
    return dsn


def export_qc(csv_path: Path) -> int:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    dsn = get_dsn()
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # DB 스키마와 동일한 순서로 내보낸다.
            cur.execute(
                """
                SELECT tag_name, min_val, max_val, max_step, max_gap_seconds,
                       allow_negative, enabled, meta,
                       warn_min, warn_max, crit_min, crit_max,
                       roc_max_per_min, spike_zscore, deadband_pct
                FROM public.influx_qc_rule
                ORDER BY tag_name
                """
            )
            rows = list(cur.fetchall())

    # Normalize meta to JSON text
    for r in rows:
        m = r.get("meta")
        if isinstance(m, (dict, list)):
            r["meta"] = json.dumps(m, ensure_ascii=False)
        elif m is None:
            r["meta"] = "{}"
        else:
            r["meta"] = str(m)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "tag_name",
                "min_val",
                "max_val",
                "max_step",
                "max_gap_seconds",
                "allow_negative",
                "enabled",
                "meta",
                "warn_min",
                "warn_max",
                "crit_min",
                "crit_max",
                "roc_max_per_min",
                "spike_zscore",
                "deadband_pct",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    return len(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "data/qc/influx_qc_rule.csv"
    count = export_qc(out)
    print(f"Exported {count} rows to {out.as_posix()}")


if __name__ == "__main__":
    main()


