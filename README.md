# CRICKO 🏏

**Cricket intelligence, reimagined.**

CRICKO is a domain-specific cricket analytics product designed to combine structured match statistics, semantic cricket knowledge and reproducible calculations to answer multi-hop questions with evidence.

## Current build

The frontend is a polished, responsive Next.js experience with:
- Natural-language cricket query interface
- Suggested analytical questions
- Evidence-backed answer surface
- Cricket-native RAG architecture story
- Mobile responsive design
- Vercel-ready deployment

The data/evaluation foundation now includes:
- Locked MVP methodology for men's T20 cricket
- Independent statistics reference implementation
- Canonical team identity layer
- 200-case golden evaluation scaffold
- Pinned Cricsheet IPL + men's T20I source archives
- SHA-256 snapshot manifest
- Git LFS storage for the source archives
- Automated MVP ingestion and validation in GitHub Actions

## MVP data scope

The pinned source snapshot covers men's IPL and men's T20 internationals, with the CRICKO MVP filter starting **2022-01-01**.

Derived metrics follow the locked definitions in [the methodology](docs/methodology.md). Matches with revised targets, no-results, or Super Over/bowl-out deciders are excluded from the deterministic MVP dataset.

Cricsheet is an upstream source and is not globally complete; CRICKO records the exact snapshot and hashes rather than implying complete world coverage.

## Planned intelligence layer

1. Cricket entity recognition
2. PostgreSQL + pgvector retrieval
3. Structured scorecard/statistics queries
4. Deterministic statistical reasoning engine
5. Live match data adapter
6. LLM answer generation with citations
7. Golden evaluation against independently verified answers
8. Separate held-out win-probability evaluation

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

For the reference implementation:

```bash
python -m pytest eval/reference -q
```

## Product principle

**The LLM should never invent a cricket statistic.**

Retrieve the evidence, calculate derived metrics deterministically, expose the filters and sample size, then let the model explain the result.

## Evaluation status

The 200-case golden set is intentionally scaffolded with numerical answers marked `PENDING_VERIFICATION`. They should only be filled after:
1. the exact pinned snapshot is ingested,
2. an independent reference calculation is produced,
3. a second implementation/source agrees,
4. hand checks cover representative matches.

Win probability is evaluated separately because it is a probabilistic model, not a single-answer lookup benchmark.

## Project docs

- [Methodology](docs/methodology.md)
- [Data contract](data/README.md)
- [Snapshot requirements](data/snapshots/README.md)
- [Reference implementation](eval/reference/README.md)
- [Golden set](eval/golden/README.md)
