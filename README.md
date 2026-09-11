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

## Running locally

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

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
