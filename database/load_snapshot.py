"""Load CRICKO's normalized JSONL and Cricsheet metadata into PostgreSQL.

Run ingestion first; see database/README.md. All writes are wrapped in one
transaction so a failed identity/FK check does not leave a partial snapshot.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg.types.json import Jsonb


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc


def competition_id(name: str | None) -> str | None:
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"competition:{slug}"


def team_resolver(entity_registry: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    aliases: dict[str, str] = {}
    teams: dict[str, dict[str, Any]] = {}
    for item in entity_registry["teams"]:
        team_id = item["id"]
        teams[team_id] = item
        for alias in [item["display_name"], *item.get("aliases", [])]:
            key = " ".join(alias.strip().casefold().split())
            existing = aliases.get(key)
            if existing and existing != team_id:
                raise ValueError(f"Ambiguous team alias {alias!r}: {existing} vs {team_id}")
            aliases[key] = team_id
    return aliases, teams


def resolve_team(name: str | None, aliases: dict[str, str], *, context: str) -> str | None:
    if name is None:
        return None
    try:
        return aliases[" ".join(name.strip().casefold().split())]
    except KeyError as exc:
        raise ValueError(f"Unmapped team {name!r} in {context}; add an explicit alias first") from exc


def load(args: argparse.Namespace) -> dict[str, int]:
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("Set DATABASE_URL or pass --database-url")

    root = Path(__file__).resolve().parents[1]
    players_doc = read_json(root / "data/collected/players-source.json")
    teams_doc = read_json(root / "data/collected/teams-source.json")
    matches = list(read_jsonl(root / "data/collected/matches-metadata.jsonl"))
    entity_doc = read_json(root / "data/entities/teams.json")
    aliases, canonical_teams = team_resolver(entity_doc)

    # Match metadata carries namespaced IDs; normalized JSONL carries the
    # source ID. Archive name is part of the join to prevent cross-archive collisions.
    match_by_source: dict[tuple[str, str], dict[str, Any]] = {}
    for match in matches:
        key = (match["source_archive"], str(match["source_match_id"]))
        if key in match_by_source:
            raise ValueError(f"Duplicate source match key: {key}")
        match_by_source[key] = match

    archive_inputs = [
        (Path(args.ipl_jsonl), "ipl_json.zip"),
        (Path(args.t20i_jsonl), "t20s_male_json.zip"),
    ]
    # Preflight every normalized row before opening the transaction. This also
    # collects observed innings and makes metadata/identity gaps fail clearly.
    delivery_paths = [(path, archive_name) for path, archive_name in archive_inputs]
    observed_innings: dict[tuple[str, int], tuple[str, str]] = {}
    included_match_keys: set[tuple[str, str]] = set()
    row_count = 0
    for path, archive_name in delivery_paths:
        for row in read_jsonl(path):
            key = (archive_name, str(row["match_id"]))
            metadata = match_by_source.get(key)
            if metadata is None:
                raise ValueError(f"No metadata match for source key {key}")
            included_match_keys.add(key)
            canonical_match_id = metadata["match_id"]
            innings_key = (canonical_match_id, int(row["innings"]))
            pair = (row["team_batting_id"], row["team_bowling_id"])
            prior = observed_innings.setdefault(innings_key, pair)
            if prior != pair:
                raise ValueError(f"Conflicting teams for innings {innings_key}: {prior} vs {pair}")
            row_count += 1

    # The metadata collector intentionally preserves all in-scope source matches,
    # including records later excluded by the stricter normalizer (for example,
    # multiple wickets on one delivery). Only persist matches with normalized rows.
    matches = [
        match for match in matches
        if (match["source_archive"], str(match["source_match_id"])) in included_match_keys
    ]
    match_by_source = {
        (match["source_archive"], str(match["source_match_id"])): match
        for match in matches
    }

    player_rows = players_doc["players"]
    team_rows = teams_doc["teams"]
    roster_rows: dict[tuple[str, str, str], str] = {}
    for match in matches:
        for player in match.get("player_roster", []):
            team_id = resolve_team(player["team_source_name"], aliases, context=match["match_id"])
            roster_rows[(player["source_player_id"], match["match_id"], team_id)] = player["name"]

    counts = {"players": len(player_rows), "teams": len(canonical_teams), "matches": len(matches),
              "innings": len(observed_innings), "deliveries": row_count, "player_match_map": len(roster_rows)}

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                for team_id, item in canonical_teams.items():
                    cur.execute(
                        """INSERT INTO teams(team_id, canonical_name, aliases) VALUES (%s,%s,%s)
                           ON CONFLICT(team_id) DO UPDATE SET canonical_name=EXCLUDED.canonical_name, aliases=EXCLUDED.aliases""",
                        (team_id, item["display_name"], Jsonb(item.get("aliases", []))),
                    )

                for player in player_rows:
                    cur.execute(
                        """INSERT INTO players(player_id, source_name, aliases_observed, source_id_types, identity_status, bio_status)
                           VALUES (%s,%s,%s,%s,%s,%s)
                           ON CONFLICT(player_id) DO UPDATE SET source_name=EXCLUDED.source_name,
                             aliases_observed=EXCLUDED.aliases_observed, source_id_types=EXCLUDED.source_id_types,
                             identity_status=EXCLUDED.identity_status, bio_status=EXCLUDED.bio_status""",
                        (player["source_player_id"], player["source_name"], Jsonb(player.get("aliases_observed", [])),
                         Jsonb(player.get("source_id_types", [])), player.get("canonical_identity_status", "SOURCE_IDENTITY_UNREVIEWED"),
                         player.get("bio_fields_status", "NOT_PROVIDED_BY_THIS_COLLECTOR")),
                    )

                # teams-source.json is an audit ledger and can contain names from
                # matches excluded by the stricter normalizer. Resolve teams only
                # when they occur in a match included in the normalized delivery set.

                for match in matches:
                    source_teams = match["teams_source_names"]
                    if len(source_teams) != 2:
                        raise ValueError(f"Expected exactly two teams for {match['match_id']}")
                    team1 = resolve_team(source_teams[0], aliases, context=match["match_id"])
                    team2 = resolve_team(source_teams[1], aliases, context=match["match_id"])
                    if team1 == team2:
                        raise ValueError(f"Both source teams resolve to {team1} in {match['match_id']}")
                    comp_name = match.get("competition") or "International T20"
                    comp_id = competition_id(comp_name)
                    cur.execute(
                        """INSERT INTO competitions(competition_id,name) VALUES (%s,%s)
                           ON CONFLICT(competition_id) DO UPDATE SET name=EXCLUDED.name""",
                        (comp_id, comp_name),
                    )
                    toss_winner = resolve_team(match.get("toss_winner_source_name"), aliases, context=match["match_id"])
                    winner = resolve_team(match.get("winner_source_name"), aliases, context=match["match_id"])
                    cur.execute(
                        """INSERT INTO matches(match_id,source_match_id,source_archive,match_date,gender,match_type,
                             competition_id,season,venue,city,team1_id,team2_id,toss_winner_id,toss_decision,winner_id,
                             outcome_by,stage,player_of_match_source_names,officials,source_data_version)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT(match_id) DO UPDATE SET source_match_id=EXCLUDED.source_match_id,
                             source_archive=EXCLUDED.source_archive,match_date=EXCLUDED.match_date,gender=EXCLUDED.gender,
                             match_type=EXCLUDED.match_type,competition_id=EXCLUDED.competition_id,season=EXCLUDED.season,
                             venue=EXCLUDED.venue,city=EXCLUDED.city,team1_id=EXCLUDED.team1_id,team2_id=EXCLUDED.team2_id,
                             toss_winner_id=EXCLUDED.toss_winner_id,toss_decision=EXCLUDED.toss_decision,
                             winner_id=EXCLUDED.winner_id,outcome_by=EXCLUDED.outcome_by,stage=EXCLUDED.stage,
                             player_of_match_source_names=EXCLUDED.player_of_match_source_names,officials=EXCLUDED.officials,
                             source_data_version=EXCLUDED.source_data_version""",
                        (match["match_id"], match["source_match_id"], match["source_archive"], date.fromisoformat(match["date"]),
                         match["gender"], match["match_type"], comp_id, str(match["season"]) if match.get("season") is not None else None,
                         match.get("venue"), match.get("city"), team1, team2, toss_winner, match.get("toss_decision"), winner,
                         Jsonb(match.get("outcome_by")) if match.get("outcome_by") is not None else None,
                         match.get("stage"), Jsonb(match.get("player_of_match_source_names", [])),
                         Jsonb(match.get("officials", {})), match.get("source_data_version")),
                    )

                current_match_ids = [m["match_id"] for m in matches]
                # Rebuild match-scoped children so changed rosters/innings cannot leave stale rows.
                cur.execute("DELETE FROM player_match_map WHERE match_id = ANY(%s)", (current_match_ids,))
                cur.execute("DELETE FROM innings WHERE match_id = ANY(%s)", (current_match_ids,))

                for (match_id, innings_number), (batting, bowling) in observed_innings.items():
                    cur.execute(
                        """INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id)
                           VALUES (%s,%s,%s,%s)
                           ON CONFLICT(match_id,innings_number) DO UPDATE SET
                             batting_team_id=EXCLUDED.batting_team_id,bowling_team_id=EXCLUDED.bowling_team_id""",
                        (match_id, innings_number, batting, bowling),
                    )

                for (player_id, match_id, team_id), name in roster_rows.items():
                    cur.execute(
                        """INSERT INTO player_match_map(player_id,match_id,team_id,source_name) VALUES (%s,%s,%s,%s)
                           ON CONFLICT(player_id,match_id,team_id) DO UPDATE SET source_name=EXCLUDED.source_name""",
                        (player_id, match_id, team_id, name),
                    )

                # Delete and replace delivery rows for the matches in this snapshot
                # to make reruns idempotent and prevent stale deliveries.
                cur.execute("DELETE FROM deliveries WHERE match_id = ANY(%s)", ([m["match_id"] for m in matches],))
                batch: list[tuple[Any, ...]] = []
                insert_sql = """INSERT INTO deliveries(match_id,innings_number,over_number,delivery_number,actual_delivery,
                    batting_team_id,bowling_team_id,batter_id,bowler_id,non_striker_id,legal_delivery,batter_faced,
                    batter_runs,extras_total,wide_runs,noball_runs,bye_runs,legbye_runs,penalty_runs,total_runs,bowler_runs,
                    dismissal_kind,dismissed_player_id,bowler_credited_wicket)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                for path, archive_name in delivery_paths:
                    for row in read_jsonl(path):
                        metadata = match_by_source[(archive_name, str(row["match_id"]))]
                        match_id = metadata["match_id"]
                        batch.append((
                            match_id, int(row["innings"]), int(row["over"]), int(row["delivery"]), str(row["actual_delivery"]),
                            row["team_batting_id"], row["team_bowling_id"], row["batter_id"], row["bowler_id"], row["non_striker_id"],
                            bool(row["legal_delivery"]), bool(row["batter_faced"]), int(row["batter_runs"]), int(row["extras_total"]),
                            int(row["wide_runs"]), int(row["noball_runs"]), int(row["bye_runs"]), int(row["legbye_runs"]),
                            int(row["penalty_runs"]), int(row["total_runs"]),
                            int(row["total_runs"]) - int(row["bye_runs"]) - int(row["legbye_runs"]) - int(row["penalty_runs"]),
                            row.get("dismissal_kind"), row.get("dismissed_player_id"),
                            bool(row.get("dismissal_kind") and row["dismissal_kind"] not in {
                                "run out", "retired hurt", "retired out", "obstructing the field"
                            }),
                        ))
                        if len(batch) >= 5000:
                            cur.executemany(insert_sql, batch)
                            batch.clear()
                if batch:
                    cur.executemany(insert_sql, batch)

                # Verify all expected entity and fact counts before transaction commit.
                current_match_ids = [m["match_id"] for m in matches]
                checks = [
                    ("matches", "SELECT COUNT(*) FROM matches WHERE match_id = ANY(%s)", current_match_ids, len(matches)),
                    ("innings", "SELECT COUNT(*) FROM innings WHERE match_id = ANY(%s)", current_match_ids, len(observed_innings)),
                    ("deliveries", "SELECT COUNT(*) FROM deliveries WHERE match_id = ANY(%s)", current_match_ids, row_count),
                    ("player_match_map", "SELECT COUNT(*) FROM player_match_map WHERE match_id = ANY(%s)", current_match_ids, len(roster_rows)),
                    ("players", "SELECT COUNT(*) FROM players WHERE player_id = ANY(%s)", [p["source_player_id"] for p in player_rows], len(player_rows)),
                    ("teams", "SELECT COUNT(*) FROM teams WHERE team_id = ANY(%s)", list(canonical_teams), len(canonical_teams)),
                ]
                persisted: dict[str, int] = {}
                for label, sql, ids, expected in checks:
                    cur.execute(sql, (ids,))
                    actual = cur.fetchone()[0]
                    persisted[label] = actual
                    if actual != expected:
                        raise RuntimeError(f"{label} count mismatch: expected {expected}, stored {actual}")

                cur.execute(
                    """SELECT COUNT(*) FROM deliveries d
                       JOIN innings i USING (match_id, innings_number)
                       WHERE d.batting_team_id <> i.batting_team_id
                          OR d.bowling_team_id <> i.bowling_team_id"""
                )
                mismatched_innings_teams = cur.fetchone()[0]
                if mismatched_innings_teams:
                    raise RuntimeError(f"Found {mismatched_innings_teams} delivery/innings team mismatches")

                cur.execute(
                    """SELECT COUNT(*) FROM deliveries
                       WHERE total_runs <> batter_runs + extras_total
                          OR bowler_runs <> total_runs - bye_runs - legbye_runs - penalty_runs
                          OR (wide_runs > 0 AND batter_faced)
                          OR ((wide_runs > 0 OR noball_runs > 0) AND legal_delivery)"""
                )
                invalid_deliveries = cur.fetchone()[0]
                if invalid_deliveries:
                    raise RuntimeError(f"Found {invalid_deliveries} delivery run/legality integrity violations")

    counts.update({f"persisted_{key}": value for key, value in persisted.items()})
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipl-jsonl", required=True, help="Normalized JSONL from the pinned IPL archive")
    parser.add_argument("--t20i-jsonl", required=True, help="Normalized JSONL from the pinned men's T20I archive")
    parser.add_argument("--database-url", help="PostgreSQL URL; defaults to DATABASE_URL")
    args = parser.parse_args()
    print(json.dumps(load(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
