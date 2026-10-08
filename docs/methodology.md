# CRICKO Analytics Methodology

This document is the contract shared by the deterministic stats engine, reference implementation, golden evaluation set, and answer layer.

## Scope
MVP covers men's senior T20 cricket: IPL and international T20 matches. ODI and Test queries are out of scope unless explicitly represented as refusal/correction cases.

## Identity
- Players use stable player IDs, never display names.
- Teams/franchises use stable IDs.
- Franchise renames map to one stable franchise identity where continuity is intended.
- India means the men's senior national team unless explicitly specified otherwise.

## Time and competition filters
- since 2022 means 2022-01-01 through the snapshot end date.
- Tournament, opposition, venue, team, player, and date-range filters are applied before aggregation.
- Super overs, DLS/revised-target matches, and abandoned/no-result matches are excluded by default for derived performance metrics and flagged when relevant.

## T20 phase definitions
- Powerplay: overs 1-6.
- Middle: overs 7-15.
- Death: overs 16-20.

### Shortened innings
Phase boundaries follow the scheduled innings length after an official reduction:
- Powerplay: first min(6, scheduled_overs) overs.
- Death: final min(5, scheduled_overs) overs.
- Middle: remaining overs between those boundaries.
- If scheduled innings is <= 6 overs, all balls are Powerplay and there is no middle/death phase.
- A phase with zero legal balls is omitted, never fabricated.

## Ball and bowling accounting
### Legal deliveries
Wides and no-balls are not legal balls.

### Bowler runs conceded
Bowler conceded runs include wides and no-ball runs charged to the bowler, but exclude byes and leg-byes.

### Bowling dismissals
Bowler wickets include dismissals credited to the bowler under standard scorecard conventions. Run-outs, retired dismissals, and obstructing-the-field are excluded.

## Batting metrics
- Strike rate = 100 * runs / legal balls faced.
- Batting average = runs / credited dismissals; undefined when dismissal count is zero.
- Rates are reported to two decimal places unless a golden case specifies otherwise.
- Undefined metrics are never silently converted to zero.

## Sample-size policy
- Phase leaderboards: 60 legal balls minimum.
- Matchups/H2H: 30 legal balls minimum.
- Other metrics inherit the minimum required by their definition.
- Explicit smaller-sample requests may be returned only with sample size and a thin-sample flag.
- If the default minimum cannot be met, CRICKO says so rather than silently lowering it.

## Missing metadata
Player hand and bowler style/type are data attributes, not inferred from names. Unknown values remain unknown and are excluded from filtered aggregates unless the query explicitly asks for unknown metadata.

## Derived metrics
Derived metrics are calculated by deterministic code before the LLM sees them. The LLM explains evidence; it does not invent or independently calculate statistics.

Every derived result carries: metric definition/version, filters, sample size, data snapshot ID, evidence references, and calculation version.

## Evaluation contract
Golden values are populated only after a dataset snapshot is pinned, an independent reference implementation exists, a second source/check is available where applicable, and match-level cases are hand-verified.

The golden set remains PENDING_VERIFICATION until those conditions are met.