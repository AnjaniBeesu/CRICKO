# CRICKO 🏏

**Cricket intelligence, reimagined.**

Cricko is a domain-specific RAG product for cricket analytics. The product direction is to combine structured match statistics, semantic cricket knowledge and live signals to answer multi-hop questions with reproducible calculations and evidence.

## Current build

The frontend is a polished, responsive Next.js experience with:
- Natural-language cricket query interface
- Suggested analytical questions
- Evidence-backed answer surface
- Live-signal cards
- Cricket-native RAG architecture story
- Mobile responsive design
- Vercel-ready deployment

## Planned intelligence layer

1. Cricket entity recognition
2. PostgreSQL + pgvector retrieval
3. Structured scorecard/statistics queries
4. Statistical reasoning engine
5. Live match data adapter
6. LLM answer generation with citations
7. Evaluation benchmark for numerical and retrieval accuracy

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Product principle

The LLM should never invent a cricket statistic. Retrieve the evidence, calculate derived metrics deterministically, then let the model explain the result.

Built for serious cricket questions.
