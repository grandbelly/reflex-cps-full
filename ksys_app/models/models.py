"""Data models for ksys_app.

This module defines two layers of models:
- UI simulation types (TypedDict) kept for reference/demo widgets.
- DB-backed DTOs (Pydantic) to validate/normalize rows from Timescale views.

Guideline:
- Performance-first pages may pass `dict` rows through to the UI.
- For sensitive or typed flows, validate with the DTOs before use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict, Union

from pydantic import BaseModel, Field, field_validator

__all__ = [
    # DTOs (Pydantic)
    "TimeseriesRow",
    "Feature5mRow",
    "LatestRow",
    "Indicator1mRow",
]


# ========= DB-backed DTOs (Pydantic) =========

class _TZModel(BaseModel):
    """Base with tz-aware datetime normalization to UTC when missing."""

    @staticmethod
    def _ensure_tz(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt


class TimeseriesRow(_TZModel):
    bucket: datetime = Field(..., description="UTC bucket timestamp")
    tag_name: str
    avg: float | None = None
    min: float | None = None
    max: float | None = None

    @field_validator("bucket")
    @classmethod
    def _tz_bucket(cls, v: datetime) -> datetime:  # noqa: N805
        return cls._ensure_tz(v)


class Feature5mRow(_TZModel):
    bucket: datetime
    tag_name: str
    mean_5m: float | None = None
    std_5m: float | None = None
    min_5m: float | None = None
    max_5m: float | None = None
    p10_5m: float | None = None
    p90_5m: float | None = None
    n_5m: int | None = None

    @field_validator("bucket")
    @classmethod
    def _tz_bucket(cls, v: datetime) -> datetime:  # noqa: N805
        return cls._ensure_tz(v)


class LatestRow(_TZModel):
    tag_name: str
    value: float | None = None
    ts: datetime

    @field_validator("ts")
    @classmethod
    def _tz_ts(cls, v: datetime) -> datetime:  # noqa: N805
        return cls._ensure_tz(v)


class Indicator1mRow(_TZModel):
    bucket: datetime
    tag_name: str
    avg: float | None = None
    sma_10: float | None = None
    sma_60: float | None = None
    bb_top: float | None = None
    bb_bot: float | None = None
    slope_60: float | None = None

    @field_validator("bucket")
    @classmethod
    def _tz_bucket(cls, v: datetime) -> datetime:  # noqa: N805
        return cls._ensure_tz(v)



