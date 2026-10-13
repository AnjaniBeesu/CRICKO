# CRICKO hosted deployment runbook

This repository now includes Dockerfile.api for a container host and the same loader used by CI. A real production deployment still requires a database-provider account, its connection string, and a backend-host account. Never put production credentials in GitHub files or browser-exposed NEXT_PUBLIC_* variables.

## 1. Create the hosted PostgreSQL database

Use a managed PostgreSQL provider (for example Neon, Railway, Supabase, or Render). Keep the database private where the provider supports private networking. Use a strong, unique password and the provider's recommended pooled connection string for the long-running API. Keep a direct connection string available for schema changes and the one-time bulk load if the provider recommends it.

Set the schema using a trusted machine with the repository checked out:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require'
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
```

Use the exact connection-string format supplied by the provider. Do not reuse the local Compose password.

## 2. Load the pinned snapshot

Run from the repository root, after Git LFS has fetched the pinned archives:

```bash
python -m pip install -r database/requirements.txt -r api/requirements.txt
python -m eval.reference.ingest data/snapshots/cricsheet/ipl_json.zip /tmp/cricko-ipl.jsonl
python -m eval.reference.ingest data/snapshots/cricsheet/t20s_male_json.zip /tmp/cricko-t20i.jsonl
python -m eval.reference.collect_cricsheet_metadata \
  --output-dir data/collected \
  data/snapshots/cricsheet/ipl_json.zip \
  data/snapshots/cricsheet/t20s_male_json.zip
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require'
python -m database.load_snapshot \
  --ipl-jsonl /tmp/cricko-ipl.jsonl \
  --t20i-jsonl /tmp/cricko-t20i.jsonl
```

Check the loader summary before proceeding. For snapshot cricsheet-mvp-t20-2026-10-08, expected counts are 2,607 matches, 5,213 innings, 599,796 deliveries, 3,746 players, 117 teams, and 57,906 player-match mappings. If source files or snapshot ID change, counts may change too. Do not expose the database to the public internet solely to make the loader work; use a temporary trusted machine or provider-supported secure access.

## 3. Deploy FastAPI

Configure the backend host to build from repository root using Dockerfile.api. Provide these runtime environment variables through the provider's secret manager:

- DATABASE_URL: hosted PostgreSQL connection string (never commit it).
- CRICKO_CORS_ORIGINS: comma-separated allowed browser origins if a browser will call the API directly. For example, the exact production Vercel origin. The current Next.js server-side proxy does not require browser CORS to reach FastAPI.

Expose port 8000 or honor the host-provided PORT. Configure the platform health check to call /healthz. Verify /healthz returns {"status":"ok","database":"connected"} before connecting the frontend.

## 4. Connect the Vercel frontend

In the Vercel project for CRICKO, set the server-side environment variable CRICKO_API_URL to the public HTTPS base URL of the deployed FastAPI service (no trailing slash required). Apply it to Production and Preview only where the backend is reachable, then redeploy the frontend. Verify the homepage leaderboard and inspect the server-side /api/stats/top-batters response.

## 5. Production hardening checklist

Before treating this as a production service:

- Keep PostgreSQL private; allow connections only from the backend and trusted loader path.
- Use provider TLS and connection pooling; set conservative connection limits.
- Add API rate limiting and request timeouts at the host/proxy layer.
- Configure monitoring for /healthz, database saturation, error rates, and API latency.
- Restrict database credentials to the minimum required permissions after loading.
- Rotate credentials if they are ever pasted into a public issue, commit, or client-side environment.
- Test deployment from the exact pinned snapshot and record its ID in release notes.

The repository contains deployment instructions and a container build, but this file does not mean a hosted database or public API has already been provisioned.
