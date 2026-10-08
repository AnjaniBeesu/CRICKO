"""Build a normalized CRICKO delivery snapshot from a Cricsheet JSON ZIP.

The command filters the locked MVP scope: men's T20, IPL plus official
international T20s from 2022 onward. Matches excluded by the methodology are
recorded with explicit reasons rather than silently disappearing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from .cricsheet_json import normalize_match
from .team_identity import UnknownTeamError
from .validate import validate_rows


def exclusion_reason(payload: dict[str, Any]) -> str | None:
    info = payload["info"]
    outcome = info.get("outcome", {})

    if info.get("gender") != "male":
        return "not_mens"
    if info.get("match_type") not in {"T20", "IT20"}:
        return "not_t20"
    year = int(info["dates"][0][:4])
    if year < 2022:
        return "before_2022"

    event_name = info.get("event", {}).get("name", "")
    if event_name != "Indian Premier League" and info.get("team_type") != "international":
        return "outside_mvp_competitions"

    if outcome.get("method") in {"D/L", "VJD"}:
        return "revised_target"
    if outcome.get("result") == "no result":
        return "no_result"
    if outcome.get("eliminator") or outcome.get("bowl_out"):
        return "super_over_or_bowl_out"

    return None


def in_mvp_scope(payload: dict[str, Any]) -> bool:
    return exclusion_reason(payload) is None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_snapshot(source_zip: str, output_jsonl: str) -> dict[str, Any]:
    source = Path(source_zip)
    output = Path(output_jsonl)
    output.parent.mkdir(parents=True, exist_ok=True)

    matches = 0
    deliveries = 0
    excluded: list[dict[str, str]] = []
    unknown_teams: set[str] = set()

    with zipfile.ZipFile(source) as archive, output.open("w", encoding="utf-8") as out:
        for name in sorted(archive.namelist()):
            if not name.endswith(".json") or name.endswith("/"):
                continue

            match_id = Path(name).stem
            with archive.open(name) as fh:
                payload = json.load(fh)

            reason = exclusion_reason(payload)
            if reason is not None:
                excluded.append({"match_id": match_id, "reason": reason})
                continue

            try:
                rows = normalize_match(payload, match_id)
            except UnknownTeamError as exc:
                excluded.append({"match_id": match_id, "reason": "unknown_team", "detail": str(exc)})
                unknown_teams.add(str(exc).split("unknown team name: ", 1)[-1].split(";", 1)[0].strip("'\""))
                continue
            except ValueError as exc:
                if "multiple wickets on one delivery require explicit handling" not in str(exc):
                    raise
                excluded.append({"match_id": match_id, "reason": "multiple_wickets_on_delivery", "detail": str(exc)})
                continue

            validate_rows(rows)
            for row in rows:
                out.write(json.dumps(row.__dict__, sort_keys=True) + "\n")

            matches += 1
            deliveries += len(rows)

    return {
        "source": str(source),
        "source_sha256": sha256_file(source),
        "output": str(output),
        "output_sha256": sha256_file(output),
        "matches": matches,
        "deliveries": deliveries,
        "excluded_matches": excluded,
        "unknown_teams": sorted(unknown_teams),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_zip")
    parser.add_argument("output_jsonl")
    args = parser.parse_args()
    print(json.dumps(build_snapshot(args.source_zip, args.output_jsonl), indent=2))


if __name__ == "__main__":
    main()
