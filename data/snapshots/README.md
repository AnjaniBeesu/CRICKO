# Dataset snapshots

A snapshot is considered immutable only when the exact source artifacts have been archived and their SHA-256 hashes recorded.

Required manifest fields:

- `snapshot_id`
- `source`
- `source_version`
- `retrieved_at`
- `coverage`
- `artifacts[]`
- `sha256`
- `match_count`
- `delivery_count`
- `excluded_matches[]`
- `notes`

Until those fields are populated from an actual downloaded release, snapshot status must remain `NOT_PINNED`.

The golden set must never use a moving URL as its data source.
