"""CRICKO API: deterministic database-backed cricket statistics."""
from __future__ import annotations

import os
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database.stats import head_to_head, phase_stats, top_batters, top_bowlers

app = FastAPI(
    title="CRICKO API",
    version="0.2.0",
    description="Deterministic cricket statistics calculated from the scoped Cricsheet snapshot.",
)

origins = [value.strip() for value in os.getenv("CRICKO_CORS_ORIGINS", "").split(",") if value.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return value


@app.get("/healthz")
def healthz() -> dict[str, str]:
    try:
        with psycopg.connect(database_url(), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "connected"}


@app.get("/stats/top-batters")
def stats_top_batters(
    limit: int = Query(default=10, ge=1, le=50),
    min_balls: int = Query(default=30, ge=0, le=100000),
    competition: str | None = Query(default=None, min_length=1, max_length=100),
) -> dict[str, Any]:
    try:
        rows = top_batters(database_url(), limit=limit, min_balls=min_balls, competition=competition)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to query cricket statistics") from exc
    return {
        "metric": "batting_runs",
        "definition": "Batter-attributed runs; balls faced follows normalized batter_faced (wides excluded, no-balls included). Strike rate = 100 × runs / balls faced.",
        "filters": {"competition": competition, "min_balls": min_balls, "limit": limit},
        "scope": "Men's IPL and international T20, 2022 onward, subject to documented ingestion exclusions.",
        "snapshot_id": "cricsheet-mvp-t20-2026-10-08",
        "count": len(rows),
        "results": rows,
    }


@app.get("/stats/top-bowlers")
def stats_top_bowlers(
    limit: int = Query(default=10, ge=1, le=50),
    min_legal_balls: int = Query(default=60, ge=0, le=100000),
    competition: str | None = Query(default=None, min_length=1, max_length=100),
) -> dict[str, Any]:
    try:
        rows = top_bowlers(database_url(), limit=limit, min_legal_balls=min_legal_balls, competition=competition)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to query bowling statistics") from exc
    return {
        "metric": "bowling_leaderboard",
        "definitions": {
            "economy": "Bowler-charged runs × 6 / legal deliveries",
            "bowling_average": "Bowler-charged runs / bowler-credited wickets; null when no credited wickets",
            "bowling_strike_rate": "Legal deliveries / bowler-credited wickets; null when no credited wickets",
        },
        "filters": {"competition": competition, "min_legal_balls": min_legal_balls, "limit": limit},
        "snapshot_id": "cricsheet-mvp-t20-2026-10-08",
        "count": len(rows),
        "results": rows,
    }


@app.get("/stats/phases")
def stats_phases(
    phase: str = Query(..., pattern="^(powerplay|middle|death)$"),
) -> dict[str, Any]:
    try:
        result = phase_stats(database_url(), phase=phase)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to query phase statistics") from exc
    return result


@app.get("/head-to-head")
def stats_head_to_head(
    batter_id: str = Query(..., min_length=1, max_length=200),
    bowler_id: str = Query(..., min_length=1, max_length=200),
    competition: str | None = Query(default=None, min_length=1, max_length=100),
) -> dict[str, Any]:
    try:
        result = head_to_head(database_url(), batter_id=batter_id, bowler_id=bowler_id, competition=competition)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to query batter-versus-bowler statistics") from exc
    return result
