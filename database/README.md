# CRICKO PostgreSQL data layer

This is the first persistence slice for the scoped Cricsheet dataset. It adds a relational schema and a deterministic loader for the existing normalized JSONL plus the source-backed metadata registries. It does **not** provide a production API or claim that player identities have been manually reconciled.

## Local setup

Requires Docker Compose, Python 3.11+, and the pinned Cricsheet archives already present under `data/snapshots/cricsheet/`.

```bash
docker compose -f database/docker-compose.yml up -d
python -m pip install -r database/requirements.txt
psql "postgresql://cricko:cricko_local_only@localhost:5432/cricko" -v ON_ERROR_STOP=1 -f database/schema.sql
```

Generate the normalized delivery JSONL from the pinned archives:

```bash
python -m eval.reference.ingest data/snapshots/cricsheet/ipl_json.zip /tmp/cricko-ipl.jsonl
python -m eval.reference.ingest data/snapshots/cricsheet/t20s_male_json.zip /tmp/cricko-t20i.jsonl
```

Load the registries and both delivery files:

```bash
export DATABASE_URL='postgresql://cricko:cricko_local_only@localhost:5432/cricko'
python -m database.load_snapshot \
  --ipl-jsonl /tmp/cricko-ipl.jsonl \
  --t20i-jsonl /tmp/cricko-t20i.jsonl
```

The loader is idempotent for the same snapshot: inserts use stable keys and update source-backed fields on conflict. It runs in a transaction; any missing team/player identity or broken foreign key aborts the transaction rather than silently inventing a mapping.

## Tables

- `teams`: canonical team IDs from `data/entities/teams.json`.
- `players`: source IDs and observed names; identity review remains explicitly pending.
- `competitions`: source competition labels.
- `matches`: source-backed metadata and explicit team/toss/winner IDs.
- `innings`: one row per observed innings.
- `deliveries`: one row per source delivery, preserving illegal deliveries, extras, dismissal data, and deterministic source coordinates.
- `player_match_map`: source roster membership by match and team.

The schema deliberately does not add fabricated player roles, batting/bowling styles, biographies, or stage values when the source does not supply them. The Cricsheet metadata collector currently leaves stage enrichment out of scope.

## Validation after loading

```sql
SELECT COUNT(*) AS matches FROM matches;
SELECT COUNT(*) AS innings FROM innings;
SELECT COUNT(*) AS deliveries FROM deliveries;
SELECT COUNT(*) AS players FROM players;
SELECT COUNT(*) AS teams FROM teams;

-- Duplicate delivery coordinates must never exist.
SELECT match_id, innings_number, over_number, delivery_number, COUNT(*)
FROM deliveries
GROUP BY 1,2,3,4
HAVING COUNT(*) > 1;

-- Innings teams should agree with delivery teams.
SELECT COUNT(*) AS mismatched_team_rows
FROM deliveries d
JOIN innings i USING (match_id, innings_number)
WHERE d.batting_team_id <> i.batting_team_id
   OR d.bowling_team_id <> i.bowling_team_id;
```

Compare counts with the ingestion summaries for this exact pinned snapshot. Do not hard-code historical counts as universal truths: a source snapshot or scope change can change the totals.

## Data integrity notes

- Team aliases are exact, case-insensitive aliases from the versioned entity registry; no fuzzy matching.
- Player IDs come from Cricsheet's registry where available. Similar names are not automatically merged.
- Match IDs are namespaced as `ipl:<source-id>` and `t20i:<source-id>` in metadata. The loader reconciles normalized source IDs to those namespaced IDs using the source archive.
- This MVP is scoped to men's IPL and international T20 from 2022 onward, with the existing explicit ingestion exclusions. It is not complete historical cricket coverage.
- Do not point this local compose configuration at a public network or reuse its development password in deployment.
