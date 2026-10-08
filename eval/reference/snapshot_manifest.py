"""Create an immutable snapshot manifest after a successful ingestion run.

Usage:
  python -m eval.reference.snapshot_manifest SOURCE_ZIP NORMALIZED_JSONL MANIFEST_JSON \
      --retrieved-at 2026-10-08 \
      --snapshot-id cricksheet-t20-mvp-2026-10-08
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_format_version(source_zip: Path) -> str | None:
    with zipfile.ZipFile(source_zip) as archive:
        candidates = sorted(
            n for n in archive.namelist()
            if n.endswith(".json") and not n.endswith("/")
        )
        if not candidates:
            raise ValueError("source ZIP contains no JSON match files")
        with archive.open(candidates[0]) as fh:
            payload = json.load(fh)
    return payload.get("meta", {}).get("data_version")


def count_normalized_matches(path: Path) -> tuple[int, int]:
    match_ids: set[str] = set()
    deliveries = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row: dict[str, Any] = json.loads(line)
            match_ids.add(row["match_id"])
            deliveries += 1
    return len(match_ids), deliveries


def build_manifest(
    source_zip: str,
    normalized_jsonl: str,
    manifest_json: str,
    snapshot_id: str,
    retrieved_at: str,
) -> dict[str, Any]:
    source = Path(source_zip)
    normalized = Path(normalized_jsonl)
    manifest_path = Path(manifest_json)

    matches, deliveries = count_normalized_matches(normalized)
    manifest = {
        "snapshot_id": snapshot_id,
        "status": "PINNED",
        "source": "Cricsheet",
        "source_version": source_format_version(source),
        "retrieved_at": retrieved_at,
        "coverage": {
            "gender": "men",
            "match_types": ["T20", "T20I"],
            "competitions": ["Indian Premier League", "international T20"],
            "scope_start": "2022-01-01",
        },
        "artifacts": [
            {
                "path": source.name,
                "kind": "source_archive",
                "sha256": sha256_file(source),
            },
            {
                "path": normalized.name,
                "kind": "normalized_jsonl",
                "sha256": sha256_file(normalized),
            },
        ],
        "match_count": matches,
        "delivery_count": deliveries,
        "excluded_matches": [],
        "notes": [
            "Manifest is immutable once published; changing any artifact requires a new snapshot_id.",
            "Golden numerical answers may only be populated against this exact snapshot.",
            "Redistribution rights must be checked against the applicable Cricsheet terms before publishing source data.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_zip")
    parser.add_argument("normalized_jsonl")
    parser.add_argument("manifest_json")
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--retrieved-at", required=True)
    args = parser.parse_args()
    print(json.dumps(build_manifest(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
