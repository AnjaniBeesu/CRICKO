"""Deterministic cricket statistics backed by PostgreSQL; no LLM in calculations."""
from __future__ import annotations

import re
from typing import Any

import psycopg
from psycopg.rows import dict_row


def competition_key(name: str | None) -> str | None:
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"competition:{slug}"


def top_batters(
    database_url: str,
    *,
    limit: int = 10,
    min_balls: int = 30,
    competition: str | None = None,
) -> list[dict[str, Any]]:
    """Rank batters by runs, then balls faced, then stable player ID.

    Runs are batter-attributed runs; balls faced uses the normalized Cricsheet
    batter_faced flag (wides excluded, no-balls included).
    """
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if min_balls < 0:
        raise ValueError("min_balls must be non-negative")

    sql = """
        SELECT
            p.player_id,
            p.source_name AS player,
            SUM(d.batter_runs)::integer AS runs,
            COUNT(*) FILTER (WHERE d.batter_faced)::integer AS balls_faced,
            COUNT(DISTINCT d.match_id)::integer AS matches,
            ROUND(
                100.0 * SUM(d.batter_runs)
                / NULLIF(COUNT(*) FILTER (WHERE d.batter_faced), 0),
                2
            )::double precision AS strike_rate
        FROM deliveries AS d
        JOIN players AS p ON p.player_id = d.batter_id
        JOIN matches AS m ON m.match_id = d.match_id
        WHERE (%s::text IS NULL OR m.competition_id = %s)
        GROUP BY p.player_id, p.source_name
        HAVING COUNT(*) FILTER (WHERE d.batter_faced) >= %s
        ORDER BY runs DESC, balls_faced DESC, p.player_id ASC
        LIMIT %s
    """
    key = competition_key(competition)
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        rows = conn.execute(sql, (key, key, min_balls, limit)).fetchall()
    return [dict(row) for row in rows]
