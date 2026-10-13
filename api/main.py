"""CRICKO API: deterministic database-backed cricket statistics."""
from __future__ import annotations

import os
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database.stats import top_batters

app = FastAPI(
    title="CRICKO API",
    version="0.1.0",
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
        rows = top_batters(
            database_url(),
            limit=limit,
            min_balls=min_balls,
            competition=competition,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to query cricket statistics") from exc
    return {
        "metric": "batting_runs",
        "definition": "Batter-attributed runs; balls faced follows the normalized Cricsheet batter_faced flag. Strike rate = 100 × runs / balls faced.",
        "filters": {"competition": competition, "min_balls": min_balls, "limit": limit},
        "scope": "Men's IPL and international T20, 2022 onward, subject to documented ingestion exclusions.",
        "count": len(rows),
        "results": rows,
    }
