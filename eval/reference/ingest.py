"""Build a normalized JSONL stream from a Cricsheet JSON ZIP.

Usage:
  python -m eval.reference.ingest path/to/ipl_json.zip path/to/output.jsonl

The command filters the CRICKO MVP scope: men's senior T20, IPL plus
international T20s from 2022 onward. It does not mutate source files.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from .cricsheet_json import normalize_match


def in_mvp_scope(payload: dict) -> bool:
    info = payload["info"]
    if info.get("gender") != "male":
        return False
    if info.get("match_type") not in {"T20", "IT20"}:
        return False
    year = int(info["dates"][0][:4])
    if year < 2022:
        return False
    event_name = info.get("event", {}).get("name", "")
    return event_name == "Indian Premier League" or info.get("team_type") == "international"


def build_snapshot(source_zip: str, output_jsonl: str) -> dict:
    source = Path(source_zip)
    output = Path(output_jsonl)
    matches = 0
    deliveries = 0
    excluded = []

    with zipfile.ZipFile(source) as archive, output.open("w", encoding="utf-8") as out:
        for name in sorted(archive.namelist()):
            if not name.endswith(".json") or name.endswith("/"):
                continue
            match_id = Path(name).stem
            with archive.open(name) as fh:
                payload = json.load(fh)

            if not in_mvp_scope(payload):
                excluded.append(match_id)
                continue

            rows = normalize_match(payload, match_id)
            for row in rows:
                out.write(json.dumps(row.__dict__, sort_keys=True) + "\n")
            matches += 1
            deliveries += len(rows)

    return {
        "source": str(source),
        "matches": matches,
        "deliveries": deliveries,
        "excluded_matches": excluded,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_zip")
    parser.add_argument("output_jsonl")
    args = parser.parse_args()
    print(json.dumps(build_snapshot(args.source_zip, args.output_jsonl), indent=2))


if __name__ == "__main__":
    main()
