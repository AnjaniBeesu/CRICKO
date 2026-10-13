"""Deterministic cricket statistics backed by PostgreSQL; no LLM in calculations."""
from __future__ import annotations

import re
from typing import Any

import psycopg
from psycopg.rows import dict_row

SNAPSHOT_ID = "cricsheet-mvp-t20-2026-10-08"


def competition_key(name: str | None) -> str | None:
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"competition:{slug}"


def _connect(database_url: str):
    return psycopg.connect(database_url, row_factory=dict_row)


def top_batters(
    database_url: str,
    *,
    limit: int = 10,
    min_balls: int = 30,
    competition: str | None = None,
) -> list[dict[str, Any]]:
    """Rank batters by runs, then balls faced, then stable player ID."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if min_balls < 0:
        raise ValueError("min_balls must be non-negative")
    key = competition_key(competition)
    sql = """
        SELECT p.player_id, p.source_name AS player,
            SUM(d.batter_runs)::integer AS runs,
            COUNT(*) FILTER (WHERE d.batter_faced)::integer AS balls_faced,
            COUNT(DISTINCT d.match_id)::integer AS matches,
            ROUND(100.0 * SUM(d.batter_runs) /
                NULLIF(COUNT(*) FILTER (WHERE d.batter_faced), 0), 2)::double precision AS strike_rate,
            ARRAY_AGG(DISTINCT d.match_id ORDER BY d.match_id) AS match_ids
        FROM deliveries d
        JOIN players p ON p.player_id = d.batter_id
        JOIN matches m ON m.match_id = d.match_id
        WHERE (%s::text IS NULL OR m.competition_id = %s)
        GROUP BY p.player_id, p.source_name
        HAVING COUNT(*) FILTER (WHERE d.batter_faced) >= %s
        ORDER BY runs DESC, balls_faced DESC, p.player_id ASC
        LIMIT %s
    """
    with _connect(database_url) as conn:
        rows = conn.execute(sql, (key, key, min_balls, limit)).fetchall()
    return [dict(row) for row in rows]


def top_bowlers(
    database_url: str,
    *,
    limit: int = 10,
    min_legal_balls: int = 60,
    competition: str | None = None,
) -> list[dict[str, Any]]:
    """Rank bowlers by credited wickets; rates use bowler-charged runs/legal balls."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if min_legal_balls < 0:
        raise ValueError("min_legal_balls must be non-negative")
    key = competition_key(competition)
    sql = """
        SELECT p.player_id, p.source_name AS player,
            COUNT(*) FILTER (WHERE d.bowler_credited_wicket)::integer AS wickets,
            SUM(d.bowler_runs)::integer AS runs_conceded,
            COUNT(*) FILTER (WHERE d.legal_delivery)::integer AS legal_balls,
            COUNT(DISTINCT d.match_id)::integer AS matches,
            ROUND(6.0 * SUM(d.bowler_runs) /
                NULLIF(COUNT(*) FILTER (WHERE d.legal_delivery), 0), 2)::double precision AS economy,
            ROUND(1.0 * SUM(d.bowler_runs) /
                NULLIF(COUNT(*) FILTER (WHERE d.bowler_credited_wicket), 0), 2)::double precision AS bowling_average,
            ROUND(1.0 * COUNT(*) FILTER (WHERE d.legal_delivery) /
                NULLIF(COUNT(*) FILTER (WHERE d.bowler_credited_wicket), 0), 2)::double precision AS bowling_strike_rate,
            ARRAY_AGG(DISTINCT d.match_id ORDER BY d.match_id) AS match_ids
        FROM deliveries d
        JOIN players p ON p.player_id = d.bowler_id
        JOIN matches m ON m.match_id = d.match_id
        WHERE (%s::text IS NULL OR m.competition_id = %s)
        GROUP BY p.player_id, p.source_name
        HAVING COUNT(*) FILTER (WHERE d.legal_delivery) >= %s
        ORDER BY wickets DESC, economy ASC NULLS LAST, p.player_id ASC
        LIMIT %s
    """
    with _connect(database_url) as conn:
        rows = conn.execute(sql, (key, key, min_legal_balls, limit)).fetchall()
    return [dict(row) for row in rows]


def phase_stats(database_url: str, *, phase: str) -> dict[str, Any]:
    """Aggregate innings output by standard T20 phase using one-based over numbers."""
    phase_bounds = {"powerplay": (1, 6), "middle": (7, 15), "death": (16, 20)}
    if phase not in phase_bounds:
        raise ValueError("phase must be powerplay, middle, or death")
    first_over, last_over = phase_bounds[phase]
    sql = """
        SELECT %s::text AS phase,
            COALESCE(SUM(d.total_runs), 0)::integer AS runs,
            COUNT(*) FILTER (WHERE d.dismissed_player_id IS NOT NULL)::integer AS wickets,
            COUNT(*) FILTER (WHERE d.legal_delivery)::integer AS legal_balls,
            COUNT(DISTINCT d.match_id)::integer AS matches,
            ARRAY_AGG(DISTINCT d.match_id ORDER BY d.match_id) AS match_ids
        FROM deliveries d
        WHERE d.over_number BETWEEN %s AND %s
    """
    with _connect(database_url) as conn:
        row = dict(conn.execute(sql, (phase, first_over, last_over)).fetchone())
    row["run_rate"] = round(6 * row["runs"] / row["legal_balls"], 2) if row["legal_balls"] else None
    row["filters"] = {"phase": phase, "over_start": first_over, "over_end": last_over}
    row["formula"] = "Run rate = total runs × 6 / legal deliveries; wickets count all recorded dismissed players."
    row["snapshot_id"] = SNAPSHOT_ID
    return row


def head_to_head(
    database_url: str,
    *,
    batter_id: str,
    bowler_id: str,
    competition: str | None = None,
) -> dict[str, Any]:
    """Batter-versus-bowler output; dismissals count only wickets credited to that bowler."""
    key = competition_key(competition)
    sql = """
        SELECT b.player_id AS batter_id, b.source_name AS batter,
            w.player_id AS bowler_id, w.source_name AS bowler,
            COALESCE(SUM(d.batter_runs), 0)::integer AS runs,
            COUNT(*) FILTER (WHERE d.batter_faced)::integer AS balls_faced,
            COUNT(*) FILTER (
                WHERE d.dismissed_player_id = d.batter_id AND d.bowler_credited_wicket
            )::integer AS dismissals,
            COUNT(DISTINCT d.match_id)::integer AS matches,
            ARRAY_AGG(DISTINCT d.match_id ORDER BY d.match_id) FILTER (WHERE d.match_id IS NOT NULL) AS match_ids
        FROM players b
        CROSS JOIN players w
        LEFT JOIN deliveries d ON d.batter_id = b.player_id AND d.bowler_id = w.player_id
        LEFT JOIN matches m ON m.match_id = d.match_id
            AND (%s::text IS NULL OR m.competition_id = %s)
        WHERE b.player_id = %s AND w.player_id = %s
        GROUP BY b.player_id, b.source_name, w.player_id, w.source_name
    """
    with _connect(database_url) as conn:
        row = conn.execute(sql, (key, key, batter_id, bowler_id)).fetchone()
    if row is None:
        raise ValueError("unknown batter_id or bowler_id")
    result = dict(row)
    result["strike_rate"] = round(100 * result["runs"] / result["balls_faced"], 2) if result["balls_faced"] else None
    result["filters"] = {"competition": competition}
    result["formula"] = "Strike rate = batter-attributed runs × 100 / balls faced; dismissals include only wickets credited to this bowler."
    result["snapshot_id"] = SNAPSHOT_ID
    return result
