# Reference layer

The reference implementation is deliberately separate from CRICKO's production engine.

## Input contract

A normalized ball record must provide:

- match_id
- innings
- over (1-based)
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

The current Cricsheet JSON format is 1.3.0. The upstream format documents stable player identifiers through the registry; team identity is kept as a separate mapping concern because the match JSON registry does not provide team IDs. citeturn1view0

The current download page lists an IPL JSON archive and reports 1,243 IPL matches; it also notes that some matches are withheld. These upstream counts are informational only until a local archive is hashed and pinned. citeturn2view0
