# Sure Shift Search Growth OS — Phased Build Roadmap

**Principle:** Each phase must be independently deployable, tested, and stable
before the next phase starts. No phase begins until the previous phase's
"Definition of Done" is met. This is what "build without error" means in
practice — small verified increments, not one giant build.

---

## Phase 0 — Foundations (no product features yet)
**Goal:** A skeleton that won't need to be rebuilt later.

- Monorepo structure (backend/, frontend/, workers/, crawler/, n8n/, infra/)
- Docker Compose: Postgres, Redis, FastAPI, Next.js, Celery worker, n8n
- CI pipeline: lint, type-check, unit tests on every commit
- Secrets management (.env + vault pattern), no secrets in code
- Base DB migrations tool (Alembic)
- Provider abstraction interfaces stubbed (empty, no logic yet):
  `LLMProvider`, `SERPProvider`
- Logging + error tracking (structured logs, Sentry or equivalent)

**Definition of Done:** `docker compose up` boots all services; CI green;
health-check endpoint returns 200.

---

## Phase 1 — Data Spine
**Modules: 1 (Business Intelligence), 47/48 (Data Quality & Source Reliability — schema only), 49 (Auth/RBAC baseline)**

- Core Postgres schema: business, services, locations, goals, customers,
  leads, quotations, bookings, revenue
- Every table carries `source`, `timestamp`, `confidence` columns from day one
  (retrofitting this later is painful — build it in now)
- Auth (JWT), RBAC roles, audit log table
- API Gateway with versioned routes

**Definition of Done:** Can create/read a business profile via API with auth;
audit log records every write.

---

## Phase 2 — Crawler + Technical SEO
**Modules: 2 (Crawler), 3 (Technical SEO Engine), 30 (Indexation Intelligence — partial)**

- Own crawler: HTTP client, HTML parser, robots.txt/sitemap parser,
  Playwright rendering, concurrency + retry + crawl budget controls
- URL normalization/canonicalization
- Store full page snapshot (title, meta, headings, links, images, structured
  data, raw + rendered HTML)
- Technical issue detector (4xx/5xx, redirects, duplicates, missing tags,
  indexability) with severity + confidence + recommended fix per issue

**Definition of Done:** Full crawl of sureshift.in completes without crashing;
issue list is reproducible on re-run; crawl respects robots.txt and rate limits.

---

## Phase 3 — Provider Abstraction + SERP/Keyword Core
**Modules: 5 (Keyword Intelligence), 6 (Query Fan-Out), 7 (SERP Intelligence), 9 (Rank Tracking)**

- Implement `SERPProvider` interface with one real backend (own infra first;
  DataForSEO only as fallback where legally/technically required)
- Keyword storage + clustering + intent classification
- Query fan-out generator (seed → related/local/commercial/question variants)
- Rank tracking with historical snapshots

**Definition of Done:** Tracking 20 seed keywords produces stored SERP
snapshots + rank history queryable by date.

---

## Phase 4 — Content & Quality Intelligence
**Modules: 4 (Page Quality), 11 (Content Intelligence), 12 (Content Gap), 13 (Content Decay), 14 (Topical Authority), 15 (Entity Graph), 16 (Schema Engine), 17 (Internal Linking), 26 (Image SEO), 27 (Video SEO)**

- Explainable page-quality scorer (no black-box single number)
- Content gap comparison (us vs competitors vs SERP vs entity graph)
- Schema detection/validation/generation pipeline (never fabricates facts —
  hard rule enforced in code, not just prompt)
- Internal linking recommender

**Definition of Done:** For one real page, system outputs a quality score
with visible component breakdown, a gap list, and a schema diff — all
verifiable against the live page.

---

## Phase 5 — Local, GBP & Reputation
**Modules: 19 (Local SEO/GBP), 20 (Local Grid), 21 (Reputation Intelligence)**

- GBP data ingestion
- Geo-grid rank tracking (lat/lng/radius)
- Review sentiment + velocity tracking

**Definition of Done:** Geo-grid map renders for Sure Shift's service area
with real ranking data for at least one keyword.

---

## Phase 6 — AEO / GEO Engine
**Modules: 22 (AEO), 23 (GEO/AI Visibility), 24 (AI Citation Graph), 25 (Brand Entity Intelligence)**

- Pluggable AI-surface providers (ChatGPT, Gemini, Perplexity, AI Overviews,
  etc.) via compliant methods only
- Citation graph: AI answer → brand mention → cited URL → source domain
- Brand/NAP consistency tracker

**Definition of Done:** One prompt from the "prompt universe" is checked
against at least one AI surface and logged with mention/citation data.

---

## Phase 7 — Competitor Intelligence
**Modules: 32–36 (Competitor monitoring, change detection, strategy classification, war room, response engine)**

- Historical competitor snapshots (reuses crawler from Phase 2)
- Change detection diffing
- Strategy classifier + response recommendation (Copy/Improve/Differentiate/Attack/Ignore)
- War-room dashboard data model

**Definition of Done:** At least 2 competitor domains tracked with a
timeline of detected changes and a classified strategy.

---

## Phase 8 — Backlinks, Performance, Logs
**Modules: 18 (Backlink Intelligence), 28 (Core Web Vitals), 29 (Log Analysis — optional if logs available)**

**Definition of Done:** CWV data (lab, not just field) available for top 20
pages; backlink list stored with source/confidence.

---

## Phase 9 — Google Search Console Integration
**Module 31**

- GSC OAuth + data pull (query/page/clicks/impressions/CTR/position)
- Anomaly + CTR-opportunity detection (positions 4–20 surfacing)

**Definition of Done:** 90 days of real GSC data ingested and queryable.

---

## Phase 10 — Opportunity, Revenue & Forecasting
**Modules: 37 (Opportunity Engine), 38 (Revenue Intelligence), 39 (Forecasting)**

- This is where everything from Phases 1–9 actually gets connected
- Opportunity score formula implemented with stored component values
- Keyword→page→click→lead→booking→revenue chain wired to real conversion
  data from Phase 1

**Definition of Done:** Top 10 opportunities for Sure Shift ranked with
full score breakdown and a revenue estimate labeled as an estimate.

---

## Phase 11 — Experiments, Causality, Volatility
**Modules: 40 (Experiment Engine), 41 (Causal Analysis), 42 (Algorithm Volatility Detection)**

**Definition of Done:** One real experiment (e.g. title rewrite on one page)
tracked end-to-end with baseline, result, and confidence level.

---

## Phase 12 — Action Engine & Autonomy
**Modules: 43 (Action Engine), 44 (Autonomy/Permission Levels), 45 (Versioning/Rollback), 46 (Change Log)**

- Start at Level 0 (observe only) / Level 1 (recommend only) for everything
- Only promote specific low-risk action types (alt text, meta suggestions) to
  Level 3 after they've proven reliable in Level 1/2 for a defined period
- Every action has before/after/rollback data from day one

**Definition of Done:** One low-risk change type can be proposed, approved,
deployed, and rolled back cleanly.

---

## Phase 13 — Security Hardening
**Module 49, full scope**

- Full RBAC, encrypted secrets, API key rotation, crawler sandboxing,
  webhook signing, CSRF, rate limiting, penetration-test pass

**Definition of Done:** Security checklist signed off before any Level 3+
autonomy is enabled in production.

---

## Phase 14 — Frontend Dashboards
- War Room (Module 35), opportunity feed, experiment tracker, change log
  viewer, forecasting views

---

## Why this order
1. Data spine and crawler first — nothing else has anything to analyze
   without them.
2. Analysis/intelligence modules before autonomy — you should never let a
   system take autonomous action based on unvalidated scoring logic.
3. Revenue/opportunity engine deliberately sits *after* the data sources
   that feed it (Phases 1–9), not before.
4. Autonomy (Phase 12) is deliberately late and security (Phase 13) gates
   it — this is the highest-risk part of the whole system.
5. n8n orchestrates *between* phases' services once they exist; it's never
   where business logic lives.

## "No errors" in practice
- Each phase ships behind its own test suite (unit + integration)
- Each phase has a Definition of Done above — treat it as a hard gate
- Staging environment mirrors prod; nothing autonomous touches the live
  site until Phase 13 is signed off
- Rollback capability (Phase 12) exists before any automated deployment
  capability is turned on
