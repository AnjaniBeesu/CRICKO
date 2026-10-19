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


@app.post("/query")
def query_cricket(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="Enter a cricket question.")
    q = question.casefold()
    # Supported deterministic query family. Never fabricate an answer for unsupported asks.
    if any(term in q for term in ("top batter", "most runs", "highest run", "leading run", "who scored the most")):
        limit = int(payload.get("limit", 10))
        try:
            rows = top_batters(database_url(), limit=max(1, min(limit, 20)), min_balls=0)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Unable to query cricket statistics") from exc
        if not rows:
            return {"question": question, "status": "no_data", "answer": "No matching batting records were found in the loaded dataset.", "results": [], "scope": "Loaded Cricsheet snapshot"}
        lines = [f"{i}. {row['player']} — {row['runs']} runs ({row['balls_faced']} balls, SR {row['strike_rate']})" for i, row in enumerate(rows, 1)]
        return {"question": question, "status": "answered", "answer": "Top run-scorers in the loaded CRICKO dataset:\n" + "\n".join(lines), "results": rows, "scope": "Loaded Cricsheet snapshot", "method": "PostgreSQL aggregate; batter-attributed runs"}
    return {"question": question, "status": "unsupported", "answer": "I can't answer that reliably yet. This CRICKO build currently supports top-run-scorer questions; comparisons, knockout filters, live scores, and broader cricket questions aren't wired up yet.", "results": [], "scope": "Loaded Cricsheet snapshot"}
