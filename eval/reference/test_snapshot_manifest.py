from pathlib import Path
import json
import zipfile

from eval.reference.snapshot_manifest import build_manifest


def test_build_manifest_records_hashes_and_counts(tmp_path: Path):
    source = tmp_path / "source.zip"
    payload = {
        "meta": {"data_version": "1.3.0"},
        "info": {
            "dates": ["2026-01-01"],
            "event": {"name": "Indian Premier League"},
            "gender": "male",
            "match_type": "T20",
            "overs": 20,
            "team_type": "club",
        },
    }
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("123.json", json.dumps(payload))

    normalized = tmp_path / "normalized.jsonl"
    normalized.write_text(
        '{"match_id":"123","innings":1}\n{"match_id":"123","innings":1}\n',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"

    result = build_manifest(
        str(source),
        str(normalized),
        str(manifest_path),
        "cricksheet-test-1",
        "2026-10-08",
    )

    assert result["status"] == "PINNED"
    assert result["source_version"] == "1.3.0"
    assert result["match_count"] == 1
    assert result["delivery_count"] == 2
    assert len(result["artifacts"][0]["sha256"]) == 64
    assert manifest_path.exists()
