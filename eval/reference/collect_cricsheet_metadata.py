"""Collect source-backed player and match metadata from pinned Cricsheet archives.

This creates an auditable source registry, not an aggressively merged canonical player
master. Similar names are preserved as separate source identities until reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any


def exclusion_reason(payload: dict[str, Any]) -> str | None:
    info = payload["info"]
    outcome = info.get("outcome", {})
    if info.get("gender") != "male":
        return "not_mens"
    if info.get("match_type") not in {"T20", "IT20"}:
        return "not_t20"
    if int(info["dates"][0][:4]) < 2022:
        return "before_2022"
    if info.get("event", {}).get("name", "") != "Indian Premier League" and info.get("team_type") != "international":
        return "outside_mvp_competitions"
    if outcome.get("method") in {"D/L", "VJD"}:
        return "revised_target"
    if outcome.get("result") == "no result":
        return "no_result"
    if outcome.get("eliminator") or outcome.get("bowl_out"):
        return "super_over_or_bowl_out"
    return None


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value or "unknown"


def collect(archives: list[Path], output_dir: Path) -> dict[str, Any]:
    players: dict[str, dict[str, Any]] = {}
    appearances: dict[str, set[str]] = defaultdict(set)
    teams: dict[str, set[str]] = defaultdict(set)
    matches: list[dict[str, Any]] = []
    excluded: dict[str, int] = defaultdict(int)
    seen_match_ids: set[str] = set()

    for archive_path in archives:
        with zipfile.ZipFile(archive_path) as archive:
            for filename in sorted(archive.namelist()):
                if not filename.endswith(".json") or filename.endswith("/"):
                    continue
                with archive.open(filename) as stream:
                    payload = json.load(stream)
                reason = exclusion_reason(payload)
                if reason:
                    excluded[reason] += 1
                    continue

                info = payload["info"]
                source_match_id = Path(filename).stem
                match_id = f"{'ipl' if info.get('event', {}).get('name') == 'Indian Premier League' else 't20i'}:{source_match_id}"
                if match_id in seen_match_ids:
                    raise ValueError(f"Duplicate match ID across archives: {match_id}")
                seen_match_ids.add(match_id)

                registry = info.get("registry", {}).get("people", {})
                name_to_source_id = {str(name): str(pid) for name, pid in registry.items()}
                team_names = [str(t) for t in info.get("teams", [])]
                for team in team_names:
                    teams[team].add(match_id)

                roster_by_team = info.get("players", {})
                roster = []
                for team, names in roster_by_team.items():
                    for raw_name in names:
                        name = str(raw_name).strip()
                        source_id = name_to_source_id.get(name)
                        if not source_id:
                            source_id = "name:" + slug(name)
                        record = players.setdefault(source_id, {
                            "source_player_id": source_id,
                            "source_name": name,
                            "aliases_observed": set(),
                            "source_id_types": set(),
                        })
                        record["aliases_observed"].add(name)
                        record["source_id_types"].add("cricsheet_registry" if source_id != "name:" + slug(name) else "name_fallback")
                        appearances[source_id].add(match_id)
                        roster.append({"team_source_name": str(team), "source_player_id": source_id, "name": name})

                outcome = info.get("outcome", {})
                toss = info.get("toss", {})
                matches.append({
                    "match_id": match_id,
                    "source_match_id": source_match_id,
                    "source_archive": archive_path.name,
                    "date": str(info.get("dates", [""])[0]),
                    "gender": info.get("gender"),
                    "match_type": info.get("match_type"),
                    "competition": info.get("event", {}).get("name") or ("International T20" if info.get("team_type") == "international" else None),
                    "season": info.get("event", {}).get("season"),
                    "teams_source_names": team_names,
                    "venue": info.get("venue"),
                    "city": info.get("city"),
                    "toss_winner_source_name": toss.get("winner"),
                    "toss_decision": toss.get("decision"),
                    "winner_source_name": outcome.get("winner"),
                    "outcome_by": outcome.get("by"),
                    "player_of_match_source_names": info.get("player_of_match", []),
                    "player_roster": roster,
                    "officials": info.get("officials", {}),
                    "source_data_version": info.get("data_version"),
                })

    player_rows = []
    for source_id, record in sorted(players.items(), key=lambda item: item[1]["source_name"].casefold()):
        player_rows.append({
            **record,
            "aliases_observed": sorted(record["aliases_observed"]),
            "source_id_types": sorted(record["source_id_types"]),
            "matches_in_snapshot": len(appearances[source_id]),
            "match_ids": sorted(appearances[source_id]),
            "canonical_identity_status": "SOURCE_IDENTITY_UNREVIEWED",
            "bio_fields_status": "NOT_PROVIDED_BY_THIS_COLLECTOR",
        })
    team_rows = [{
        "source_team_name": name,
        "matches_in_snapshot": len(ids),
        "match_ids": sorted(ids),
        "canonical_team_id": None,
        "mapping_status": "REQUIRES_EXPLICIT_TEAM_RESOLUTION",
    } for name, ids in sorted(teams.items(), key=lambda item: item[0].casefold())]

    output_dir.mkdir(parents=True, exist_ok=True)
    players_path = output_dir / "players-source.json"
    teams_path = output_dir / "teams-source.json"
    matches_path = output_dir / "matches-metadata.jsonl"
    players_path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "source": "Cricsheet JSON",
        "scope": "men's IPL and international T20, 2022 onward, subject to ingestion exclusions",
        "source_archive_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archives},
        "player_count": len(player_rows),
        "players": player_rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    teams_path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "source": "Cricsheet JSON",
        "team_count": len(team_rows),
        "teams": team_rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with matches_path.open("w", encoding="utf-8") as stream:
        for row in sorted(matches, key=lambda r: (r["date"], r["match_id"])):
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "matches": len(matches),
        "players_source_identities": len(player_rows),
        "source_team_names": len(team_rows),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "outputs": [str(players_path), str(teams_path), str(matches_path)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/collected")
    parser.add_argument("archives", nargs="+")
    args = parser.parse_args()
    print(json.dumps(collect([Path(p) for p in args.archives], Path(args.output_dir)), indent=2))


if __name__ == "__main__":
    main()
