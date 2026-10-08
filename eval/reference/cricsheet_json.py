"""Normalize Cricsheet JSON deliveries into CRICKO's reference Ball contract.

This adapter is intentionally dependency-free and does not perform analytics.
It preserves source semantics so the independent reference calculations remain
separate from any future production engine.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterator
from eval.reference.team_identity import TeamResolver, load_team_resolver

@dataclass(frozen=True)
class NormalizedDelivery:
    match_id: str
    date: str
    competition: str | None
    match_type: str
    gender: str
    team_batting_id: str
    team_bowling_id: str
    innings: int
    scheduled_overs: int
    over: int
    delivery: int
    batter_id: str
    bowler_id: str
    non_striker_id: str
    legal_delivery: bool
    batter_runs: int
    extras_total: int
    wide_runs: int
    noball_runs: int
    bye_runs: int
    legbye_runs: int
    penalty_runs: int
    total_runs: int
    dismissal_kind: str | None
    dismissed_player_id: str | None

def _id(registry: dict[str, str], name: str) -> str:
    try:
        return registry[name]
    except KeyError as exc:
        raise ValueError(f"player missing from registry: {name}") from exc

def _extras(delivery: dict[str, Any]) -> dict[str, int]:
    extras = delivery.get("extras", {})
    return {
        "wides": int(extras.get("wides", 0)),
        "noballs": int(extras.get("noballs", 0)),
        "byes": int(extras.get("byes", 0)),
        "legbyes": int(extras.get("legbyes", 0)),
        "penalty": int(extras.get("penalty", 0)),
    }

def _dismissal(delivery: dict[str, Any], registry: dict[str, str]) -> tuple[str | None, str | None]:
    wickets = delivery.get("wickets", [])
    if not wickets:
        return None, None
    if len(wickets) != 1:
        raise ValueError("multiple wickets on one delivery require explicit handling")
    wicket = wickets[0]
    kind = wicket.get("kind")
    player = wicket.get("player_out")
    if not kind or not player:
        raise ValueError("incomplete wicket record")
    return kind, _id(registry, player)

def normalize_match(
    payload: dict[str, Any],
    match_id: str,
    team_resolver: TeamResolver | None = None,
) -> list[NormalizedDelivery]:
    """Normalize one Cricsheet JSON match into one row per delivery."""
    info = payload["info"]
    registry = info["registry"]["people"]
    teams = info["teams"]
    if len(teams) != 2:
        raise ValueError(f"expected exactly two teams, got {len(teams)}")

    resolver = team_resolver or load_team_resolver()
    team_ids = {team: resolver.resolve(team) for team in teams}

    date = info["dates"][0]
    competition = info.get("event", {}).get("name")
    match_type = info["match_type"]
    gender = info["gender"]
    scheduled_overs = int(info.get("overs", 20))

    rows: list[NormalizedDelivery] = []
    for innings_number, innings in enumerate(payload.get("innings", []), start=1):
        batting_team = innings["team"]
        bowling_team = next(team for team in teams if team != batting_team)
        for over_obj in innings.get("overs", []):
            over_number = int(over_obj["over"])
            for delivery_index, raw in enumerate(over_obj.get("deliveries", []), start=1):
                ex = _extras(raw)
                runs = raw["runs"]
                dismissal_kind, dismissed_id = _dismissal(raw, registry)
                rows.append(
                    NormalizedDelivery(
                        match_id=match_id,
                        date=date,
                        competition=competition,
                        match_type=match_type,
                        gender=gender,
                        team_batting_id=team_ids[batting_team],
                        team_bowling_id=team_ids[bowling_team],
                        innings=innings_number,
                        scheduled_overs=scheduled_overs,
                        over=over_number,
                        delivery=delivery_index,
                        batter_id=_id(registry, raw["batter"]),
                        bowler_id=_id(registry, raw["bowler"]),
                        non_striker_id=_id(registry, raw["non_striker"]),
                        legal_delivery=(ex["wides"] == 0 and ex["noballs"] == 0),
                        batter_runs=int(runs["batter"]),
                        extras_total=int(runs["extras"]),
                        wide_runs=ex["wides"],
                        noball_runs=ex["noballs"],
                        bye_runs=ex["byes"],
                        legbye_runs=ex["legbyes"],
                        penalty_runs=ex["penalty"],
                        total_runs=int(runs["total"]),
                        dismissal_kind=dismissal_kind,
                        dismissed_player_id=dismissed_id,
                    )
                )
    return rows

def iter_match_deliveries(payloads: Iterator[tuple[str, dict[str, Any]]]) -> Iterator[NormalizedDelivery]:
    """Normalize multiple (match_id, payload) pairs lazily."""
    for match_id, payload in payloads:
        yield from normalize_match(payload, match_id)
