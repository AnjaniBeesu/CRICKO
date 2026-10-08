# Reference layer

The reference implementation is deliberately separate from CRICKO's production engine.

## Input contract

A normalized ball record must provide:

- match_id
- innings
- over (1-based after Cricsheet normalization)
- legal_delivery
- batter_id
- bowler_id
- batter_runs
- total_runs
- bowler_runs
- batter_faced
- batter_dismissed
- bowler_credited_wicket
- dismissal_kind

The production ingestion layer is responsible for mapping a source dataset into this contract.

## Golden-set workflow

1. Pin a dataset snapshot.
2. Normalize it into the input contract.
3. Run these calculations independently of the production engine.
4. Reconcile selected outputs against Statsguru/manual checks.
5. Hand-check match-level cases.
6. Populate expected_result in the golden JSONL.
7. Run the evaluation harness before release.

Do not import production query-engine code into this package. Independence is the point.

## Cricsheet adapter

Cricsheet's official JSON format is normalized by `cricsheet_json.py`, then checked by `validate.py`. `ingest.py` accepts a downloaded JSON ZIP and emits deterministic JSONL for the MVP scope (men's T20/IT20, IPL + international, from 2022 onward).

The current Cricsheet JSON format is 1.3.0. The adapter resolves player IDs from the source registry and team IDs through the versioned CRICKO team alias registry. Source team names that are not explicitly mapped fail loudly; there is no fuzzy fallback.

To create a reproducible local snapshot:

`python -m eval.reference.ingest SOURCE_ZIP NORMALIZED_JSONL`

Then create the immutable manifest:

`python -m eval.reference.snapshot_manifest SOURCE_ZIP NORMALIZED_JSONL MANIFEST_JSON --snapshot-id <id> --retrieved-at <YYYY-MM-DD>`

The manifest records SHA-256 hashes for both source and normalized artifacts. Golden numerical answers must not be populated until this manifest is pinned and independently checked.

See the upstream [Cricsheet JSON format](https://cricsheet.org/format/json/) and [downloads](https://cricsheet.org/downloads/) for the source format and current availability.
