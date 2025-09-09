from __future__ import annotations

import os
import psycopg
from psycopg_pool import AsyncConnectionPool


def _dsn() -> str:
    dsn = os.environ.get("TS_DSN", "")
    if not dsn:
        raise RuntimeError("TS_DSN is not set in environment")
    return dsn

POOL: AsyncConnectionPool | None = None


def get_pool() -> AsyncConnectionPool:
    global POOL
    if POOL is None:
        POOL = AsyncConnectionPool(_dsn(), min_size=1, max_size=10, kwargs={"autocommit": True})
    return POOL


async def q(sql: str, params: tuple | dict, timeout: float = 8.0):
    pool = get_pool()
    async with pool.connection(timeout=timeout) as conn:
        # Set a per-session statement timeout to avoid hanging
        await conn.execute("SET LOCAL statement_timeout = '5s'")
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def execute_query(sql: str, params: tuple | dict, timeout: float = 8.0):
    """Execute SQL without expecting results (for INSERT, UPDATE, DELETE)"""
    pool = get_pool()
    async with pool.connection(timeout=timeout) as conn:
        # Set a per-session statement timeout to avoid hanging
        await conn.execute("SET LOCAL statement_timeout = '5s'")
        async with conn.cursor() as cur:
            await cur.execute(sql, params)


