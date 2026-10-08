"""Integrity checks for normalized CRICKO delivery rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .cricsheet_json import NormalizedDelivery


def validate_rows(rows: Iterable[NormalizedDelivery]) -> None:
    seen: set[tuple[str, int, int, int]] = set()
    previous_over: dict[tuple[str, int], int] = {}

    for row in rows:
        key = (row.match_id, row.innings, row.over, row.delivery)
        if key in seen:
            raise ValueError(f"duplicate delivery identifier: {key}")
        seen.add(key)

        if row.over < 0 or row.delivery < 1:
            raise ValueError(f"invalid over/delivery: {key}")
        if min(
            row.batter_runs,
            row.extras_total,
            row.wide_runs,
            row.noball_runs,
            row.bye_runs,
            row.legbye_runs,
            row.penalty_runs,
            row.total_runs,
        ) < 0:
            raise ValueError(f"negative run value: {key}")

        expected_total = row.batter_runs + row.extras_total
        if row.total_runs != expected_total:
            raise ValueError(f"run total mismatch: {key}")

        if row.legal_delivery and (row.wide_runs or row.noball_runs):
            raise ValueError(f"illegal delivery marked legal: {key}")

        innings_key = (row.match_id, row.innings)
        prior = previous_over.get(innings_key)
        if prior is not None and row.over < prior:
            raise ValueError(f"over order regressed: {key}")
        previous_over[innings_key] = row.over
