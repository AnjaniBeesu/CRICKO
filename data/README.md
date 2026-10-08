# CRICKO data layer

The repository does not commit the full cricket dataset. Datasets are downloaded into a local data directory or CI artifact, normalized, and identified by an immutable snapshot manifest.

## Required flow

1. Download a fixed source release.
2. Record source URL, retrieval timestamp, source version/release, and SHA-256 hashes.
3. Normalize source records into CRICKO's canonical ball schema.
4. Validate innings, deliveries, runs, wickets, teams, players, dates, and competition metadata.
5. Emit a snapshot manifest under `data/snapshots/`.
6. Run the independent reference tests.
7. Only then populate golden numerical answers.

## Canonical ball schema

Each normalized delivery should contain at minimum:

- `match_id`
- `date`
- `competition`
- `match_type`
- `gender`
- `team_batting_id`
- `team_bowling_id`
- `innings`
- `scheduled_overs`
- `over`
- `delivery`
- `batter_id`
- `bowler_id`
- `non_striker_id`
- `legal_delivery`
- `batter_runs`
- `extras_total`
- `wide_runs`
- `noball_runs`
- `bye_runs`
- `legbye_runs`
- `penalty_runs`
- `total_runs`
- `dismissal_kind`
- `dismissed_player_id`

Player and team metadata must use stable IDs. Display names belong in a separate dimension table.

## Integrity checks

An ingestion run must fail loudly on:

- duplicate delivery identifiers
- missing match/team/player IDs
- impossible over or delivery values
- negative run values
- innings exceeding scheduled overs without an explicit reduced-innings/super-over explanation
- contradictory dismissal metadata
- unknown competition scope when an MVP filter depends on it

Never silently repair malformed source records. Record exclusions and reasons in the snapshot manifest.
