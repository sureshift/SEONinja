# Sure Shift Search Growth OS

Autonomous SEO + AEO + GEO Search Growth Operating System.
Built in gated phases — see `docs/phased-roadmap.md`.

## Status: Phase 1 complete ✅ (Data Spine)

- Postgres schema: businesses, services, locations, business_goals,
  customers, leads, quotations, bookings, revenue, users, audit_log
- Every business-data table carries `source` + `confidence` + timestamps
  from day one (Module 47/48 groundwork)
- JWT auth, 3-role RBAC (admin/editor/viewer), first registered user
  becomes admin (bootstrap), audit log written on every business write
- Alembic migrations, tested against real Postgres (not SQLite)
- 11/11 gate tests passing (Phase 0: 4, Phase 1: 7)

### Running the migration (required once per environment)

```bash
# Standalone:
cd backend && alembic upgrade head

# Integrated into the real stack:
docker compose -f docker-compose.yml -f sureshift-search-os/infra/docker-compose.searchos.yml \
  --env-file .env exec searchos-api alembic upgrade head
```

## Status: Phase 2 complete ✅ (Crawler + Technical SEO)

- Own crawler: BFS with concurrency control, robots.txt compliance,
  sitemap discovery (incl. sitemap-index nesting), redirect chain
  tracking, URL normalization/canonicalization
- Extracts: title, meta description, headings, word count, canonical,
  robots meta, JSON-LD structured data, Open Graph tags, images, links
- Technical SEO detector: 4xx/5xx, redirect chains, missing/duplicate
  titles & descriptions, missing/multiple H1, missing canonical, noindex,
  thin content, orphan pages
- Tested against a REAL local HTTP server (real sockets, real robots.txt
  fetch, real redirect-following) with deliberately planted issues - not
  mocked responses
- 21/21 gate tests passing (4 Phase 0 + 7 Phase 1 + 10 Phase 2)

### Known gap: no JavaScript rendering yet
The roadmap's Module 2 calls for Playwright rendering to catch JS-generated
content. This phase only fetches raw HTML via httpx - correct for
sureshift.in's WordPress pages (server-rendered), but it will silently
under-report on any page that relies on client-side rendering. Not
implemented in Phase 2 because it wasn't needed for the current
site and adds real complexity (headless browser process management,
resource limits) - flagging it explicitly here rather than letting the
gap go unnoticed. Add it if/when a JS-heavy property gets onboarded.

### Note on testing sureshift.in itself
This sandbox's network can't reach sureshift.in directly, so Phase 2 was
verified against a synthetic local test site instead (same crawler code,
real HTTP, just not the live domain). The first real crawl of
sureshift.in itself happens when triggered via the deployed API - see
below for the exact call.

### Triggering a real crawl (once deployed)

```bash
# 1. Log in, grab a token (see Phase 1 section above for register/login)
# 2. Get your business_id from GET /api/v1/businesses
# 3. Start the crawl:
curl -X POST http://localhost:8000/api/v1/crawl-jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"business_id": "<id>", "start_url": "https://sureshift.in", "max_pages": 50, "max_depth": 3}'

# Runs synchronously - the response IS the completed job. Then:
curl http://localhost:8000/api/v1/crawl-jobs/<job_id>/pages -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/v1/crawl-jobs/<job_id>/issues -H "Authorization: Bearer $TOKEN"
```

## Status: Phase 3 complete ✅ (Provider Abstraction + SERP/Keyword Core)

- `SERPProvider` implemented for real: `DataForSEOProvider` (working
  client against DataForSEO's documented API contract) + `OwnSERPProvider`
  (deliberately NOT a Google scraper - see class docstring for why)
- Keyword storage, query fan-out (question/comparison/commercial/
  transactional/local variants), rank tracking with change detection
  (gained/lost/newly_ranked/dropped_out/unchanged)
- API: `/api/v1/keywords` (create/list), `/{id}/fanout`, `/{id}/rank-check`
- 49/49 gate tests passing (4 P0 + 7 P1 + 10 P2 + 28 P3)

### Important caveat: DataForSEO field mapping unverified against a live account
No DataForSEO credentials were available while building this. The client
was built against their publicly documented API contract and tested
against a real mock server replicating that contract (real HTTP, real
auth headers) - but **the exact response field names have not been
confirmed against a real live call**. Before relying on this in
production: add real `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD` to `.env`,
run one real `rank-check` call, and compare the actual response shape
against `app/providers/serp_provider.py`'s `_parse_organic_response` -
adjust field names there if anything doesn't match.

### Setting up DataForSEO (when ready)
Add to `.env`:
```
DATAFORSEO_LOGIN=<your login>
DATAFORSEO_PASSWORD=<your password>
```
And change `SERP_PROVIDER=own` to `SERP_PROVIDER=dataforseo` in the
`searchos-api` service environment (`infra/docker-compose.searchos.yml`).

## Running locally (standalone, no other services required)

```bash
cp .env.example .env
docker compose -f docker-compose.standalone.yml up --build
curl http://localhost:8000/health
```

## Running integrated into the existing FreightIt/SureShift stack

This is the real deployment target — see `infra/docker-compose.searchos.yml`
and `infra/postgres-init-addendum.md` for the exact steps (one line added
to your existing `postgres-init` service — that's it, no new env vars).
Summary:

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

## Next: Phase 4 — Content & Quality Intelligence
Page quality scoring, content gap analysis, schema engine, internal
linking recommendations. Not started yet.
