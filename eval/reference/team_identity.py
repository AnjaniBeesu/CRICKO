"""Resolve Cricsheet team display names to stable CRICKO team IDs.

Unknown names fail loudly. Aliases are explicit data, never fuzzy-matched.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class UnknownTeamError(ValueError):
    pass

class TeamResolver:
    def __init__(self, teams: dict[str, Any]):
        aliases: dict[str, str] = {}
        canonical: dict[str, str] = {}
        for team in teams["teams"]:
            team_id = team["id"]
            canonical[team_id] = team["display_name"]
            for alias in team["aliases"]:
                key = self._key(alias)
                if key in aliases and aliases[key] != team_id:
                    raise ValueError(f"team alias collision: {alias}")
                aliases[key] = team_id
        self._aliases = aliases
        self._canonical = canonical

    @staticmethod
    def _key(name: str) -> str:
        return " ".join(name.strip().casefold().split())

    def resolve(self, source_name: str) -> str:
        try:
            return self._aliases[self._key(source_name)]
        except KeyError as exc:
            raise UnknownTeamError(
                f"unknown team name: {source_name!r}; add an explicit alias before ingestion"
            ) from exc

    def display_name(self, team_id: str) -> str:
        try:
            return self._canonical[team_id]
        except KeyError as exc:
            raise UnknownTeamError(f"unknown canonical team ID: {team_id!r}") from exc

def load_team_resolver(path: str | Path | None = None) -> TeamResolver:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "data" / "entities" / "teams.json"
    with Path(path).open(encoding="utf-8") as fh:
        return TeamResolver(json.load(fh))
