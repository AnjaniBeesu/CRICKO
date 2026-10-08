from __future__ import annotations

"""Independent, dependency-light reference calculations for CRICKO.

This module is intentionally separate from the production query engine.
It operates on normalized ball records and is suitable for generating
golden answers once a pinned dataset snapshot is available.
"""

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Ball:
    match_id: str
    innings: int
    over: int
    legal_delivery: bool
    batter_id: str
    bowler_id: str
    batter_runs: int
    total_runs: int
    bowler_runs: int
    batter_faced: bool
    batter_dismissed: bool
    bowler_credited_wicket: bool
    dismissal_kind: Optional[str] = None


def phase_for_over(over_one_based: int, scheduled_overs: int = 20) -> str:
    if scheduled_overs <= 0:
        raise ValueError("scheduled_overs must be positive")
    if over_one_based < 1 or over_one_based > scheduled_overs:
        raise ValueError("over outside scheduled innings")
    if over_one_based <= min(6, scheduled_overs):
        return "powerplay"
    if over_one_based > max(scheduled_overs - 5, 6):
        return "death"
    return "middle"


def batting_summary(balls: Iterable[Ball], batter_id: str) -> dict:
    rows = [b for b in balls if b.batter_id == batter_id]
    runs = sum(b.batter_runs for b in rows)
    legal_balls = sum(1 for b in rows if b.batter_faced and b.legal_delivery)
    dismissals = sum(
        1
        for b in rows
        if b.batter_dismissed and b.dismissal_kind not in {
            "retired_hurt", "retired_out", "obstructing_the_field"
        }
    )
    strike_rate = (100.0 * runs / legal_balls) if legal_balls else None
    average = (runs / dismissals) if dismissals else None
    return {
        "runs": runs,
        "legal_balls": legal_balls,
        "dismissals": dismissals,
        "strike_rate": strike_rate,
        "average": average,
    }


def bowling_summary(balls: Iterable[Ball], bowler_id: str) -> dict:
    rows = [b for b in balls if b.bowler_id == bowler_id]
    legal_balls = sum(1 for b in rows if b.legal_delivery)
    conceded = sum(b.bowler_runs for b in rows)
    wickets = sum(1 for b in rows if b.bowler_credited_wicket)
    economy = (6.0 * conceded / legal_balls) if legal_balls else None
    return {
        "runs_conceded": conceded,
        "legal_balls": legal_balls,
        "wickets": wickets,
        "economy": economy,
    }


def require_min_sample(sample_size: int, minimum: int) -> dict:
    return {
        "sample_size": sample_size,
        "minimum": minimum,
        "thin_sample": sample_size < minimum,
        "eligible": sample_size >= minimum,
    }
