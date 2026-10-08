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
