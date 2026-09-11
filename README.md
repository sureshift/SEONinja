# Sure Shift Search Growth OS

Autonomous SEO + AEO + GEO Search Growth Operating System.
Built in gated phases — see `docs/phased-roadmap.md`.

## Status: Phase 0 complete ✅

- FastAPI backend boots and responds on `/health`
- Config loads from environment (no hard-coded values)
- `LLMProvider` and `SERPProvider` abstractions stubbed, factory-based,
  swappable via config
- Docker Compose defines Postgres + Redis + API
- CI runs the test suite on every push
- 4/4 Phase 0 gate tests passing

## Running locally (standalone, no other services required)

```bash
cp .env.example .env
docker compose -f docker-compose.standalone.yml up --build
curl http://localhost:8000/health
```

## Running integrated into the existing FreightIt/SureShift stack

This is the real deployment target — see `infra/docker-compose.searchos.yml`
and `infra/postgres-init-addendum.md` for the exact steps (one line added
to your existing `postgres-init` service, one new env var). Summary:

```bash
cd ~/SureShiftERP
docker compose -f docker-compose.yml -f sureshift-search-os/infra/docker-compose.searchos.yml \
  --env-file .env up -d --build searchos-api
curl http://localhost:8000/health
```

Runs on the existing `freight-net` network, using the shared Postgres
(dedicated `searchos_db`) and Redis (dedicated DB index `2`), and reuses
`LM_STUDIO_URL` for the `LMStudioProvider`.

## Running tests without Docker

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## Next: Phase 1 — Data Spine
Core business/services/locations/leads schema, auth, RBAC, audit log.
Not started yet — do not build on top of this repo assuming Phase 1
exists until its own gate tests pass.
