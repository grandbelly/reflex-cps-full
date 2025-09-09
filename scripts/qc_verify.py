from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import psycopg
from psycopg.rows import dict_row


FIELDS = [
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
]


def get_dsn() -> str:
    dsn = os.environ.get("TS_DSN")
    if not dsn:
        raise RuntimeError("TS_DSN is not set in environment")
    return dsn


def _norm_val(k: str, v: Any) -> str:
    if v is None:
        return ""
    if k in {"min_val", "max_val", "max_step"}:
        try:
            return ("%g" % float(v))
        except Exception:
            return str(v)
    if k in {"max_gap_seconds"}:
        try:
            return str(int(v))
        except Exception:
            return str(v)
    if k in {"allow_negative", "enabled"}:
        s = str(v).strip().lower()
        return "True" if s in {"1", "true", "t", "yes"} else ("False" if s in {"0", "false", "f", "no"} else s)
    return str(v)


def read_csv(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rec = {k: _norm_val(k, row.get(k)) for k in FIELDS}
            rows.append(rec)
    rows.sort(key=lambda x: x["tag_name"])
    return rows


def read_db() -> List[Dict[str, str]]:
    dsn = get_dsn()
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
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
            raw = list(cur.fetchall())
    rows: List[Dict[str, str]] = []
    for r in raw:
        rows.append({k: _norm_val(k, r.get(k)) for k in FIELDS})
    return rows


def diff(a: List[Dict[str, str]], b: List[Dict[str, str]]) -> List[str]:
    out: List[str] = []
    a_map = {r["tag_name"]: r for r in a}
    b_map = {r["tag_name"]: r for r in b}
    for t in sorted(set(a_map) | set(b_map)):
        ra, rb = a_map.get(t), b_map.get(t)
        if ra is None:
            out.append(f"CSV missing tag {t}")
            continue
        if rb is None:
            out.append(f"DB missing tag {t}")
            continue
        for k in FIELDS:
            va, vb = ra.get(k, ""), rb.get(k, "")
            if va != vb:
                out.append(f"Mismatch {t}.{k}: CSV={va} DB={vb}")
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data/qc/influx_qc_rule.csv"
    csv_rows = read_csv(csv_path)
    db_rows = read_db()
    problems = diff(csv_rows, db_rows)
    if problems:
        print("QC drift detected:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("QC OK: CSV and DB are in sync.")


if __name__ == "__main__":
    main()


