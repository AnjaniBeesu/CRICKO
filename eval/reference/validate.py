"""Integrity checks for normalized CRICKO delivery rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .cricsheet_json import NormalizedDelivery


def validate_rows(rows: Iterable[NormalizedDelivery]) -> None:
    seen: set[tuple[str, int, int, int]] = set()
    previous_over: dict[tuple[str, int], int] = {}
    previous_actual: dict[tuple[str, int], str] = {}

    for row in rows:
        key = (row.match_id, row.innings, row.over, row.delivery)
        if key in seen:
            raise ValueError(f"duplicate delivery identifier: {key}")
        seen.add(key)

        if row.over < 0 or row.delivery < 1:
            raise ValueError(f"invalid over/delivery: {key}")
        if row.over >= row.scheduled_overs:
            raise ValueError(f"over exceeds scheduled innings: {key}")
        if not row.actual_delivery:
            raise ValueError(f"missing actual_delivery: {key}")

        values = (
            row.batter_runs, row.extras_total, row.wide_runs, row.noball_runs,
            row.bye_runs, row.legbye_runs, row.penalty_runs, row.total_runs,
        )
        if min(values) < 0:
            raise ValueError(f"negative run value: {key}")

        if row.total_runs != row.batter_runs + row.extras_total:
            raise ValueError(f"run total mismatch: {key}")

        if row.extras_total != (
            row.wide_runs + row.noball_runs + row.bye_runs +
            row.legbye_runs + row.penalty_runs
        ):
            raise ValueError(f"extras breakdown mismatch: {key}")

        if row.legal_delivery and (row.wide_runs or row.noball_runs):
            raise ValueError(f"illegal delivery marked legal: {key}")
        if row.batter_faced and row.wide_runs:
            raise ValueError(f"wide marked as batter faced: {key}")

        innings_key = (row.match_id, row.innings)
        prior = previous_over.get(innings_key)
        if prior is not None and row.over < prior:
            raise ValueError(f"over order regressed: {key}")
        previous_over[innings_key] = row.over

        prior_actual = previous_actual.get(innings_key)
        if prior_actual is not None:
            # Actual delivery is a display string such as 0.1 or 0.10. We
            # only require it to be parseable here; source ordering is checked
            # through the over/delivery sequence above.
            try:
                int(str(row.actual_delivery).split(".", 1)[0])
            except ValueError as exc:
                raise ValueError(f"invalid actual_delivery: {key}") from exc
        previous_actual[innings_key] = row.actual_delivery
