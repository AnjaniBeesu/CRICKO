"""Build the immutable CRICKO source manifest for pinned Cricsheet archives."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SOURCES = (
    ("ipl_json.zip", "https://cricsheet.org/downloads/ipl_json.zip", "IPL"),
    ("t20s_male_json.zip", "https://cricsheet.org/downloads/t20s_male_json.zip", "T20 internationals"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_archive(path: Path) -> tuple[str, int]:
    versions: set[str] = set()
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".json")]
        if not names:
            raise ValueError(f"{path}: no JSON match files")
        for name in names:
            with archive.open(name) as handle:
                payload = json.load(handle)
            version = payload.get("meta", {}).get("data_version")
            if version:
                versions.add(str(version))
        bad = archive.testzip()
        if bad:
            raise ValueError(f"{path}: corrupt ZIP member {bad}")
    if len(versions) != 1:
        raise ValueError(f"{path}: unexpected data versions {sorted(versions)}")
    return next(iter(versions)), len(names)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/snapshots/cricsheet")
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/snapshots/mvp-t20.json")

    artifacts = []
    versions = set()
    for filename, url, label in SOURCES:
        path = root / filename
        version, match_count = inspect_archive(path)
        versions.add(version)
        artifacts.append(
            {
                "name": filename,
                "source_url": url,
                "coverage_label": label,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
                "source_match_files": match_count,
            }
        )

    if len(versions) != 1:
        raise ValueError(f"archives disagree on Cricsheet data version: {sorted(versions)}")

    retrieved_at = datetime.now(timezone.utc).date().isoformat()
    manifest = {
        "snapshot_id": f"cricsheet-mvp-t20-{retrieved_at}",
        "status": "PINNED",
        "source": "Cricsheet",
        "source_format": "JSON",
        "source_version": next(iter(versions)),
        "source_license": "Open Data Commons Attribution License",
        "source_download_page": "https://cricsheet.org/downloads/",
        "retrieved_at": retrieved_at,
        "coverage": {
            "gender": "men",
            "match_types": ["T20", "T20I"],
            "competitions": ["Indian Premier League", "international T20"],
            "scope_start": "2022-01-01",
            "note": "Pinned source archives; production ingestion applies MVP filters and exclusions.",
        },
        "artifacts": artifacts,
        "notes": [
            "Source archives are stored with Git LFS and pinned by SHA-256.",
            "Create a new snapshot_id rather than replacing a pinned archive.",
            "Generate numerical golden answers only from this exact snapshot after independent verification.",
            "Cricsheet withholds some matches; this snapshot must not be described as globally complete.",
        ],
    }
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
