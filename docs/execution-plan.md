# SerpTank — Project Overhaul & Execution Document

> **Status:** approved 2026-09-24. This is the living roadmap; module PRs update it when decisions change.

_Phase 1 audit and Phase 2 plan · 2026-09-24 · branch `claude/laughing-archimedes-9woi38` · rev 2 (Google-first classic SEO plus AI search)_

---

## 0. Context

You asked me to find out what this unfinished project is meant to be, audit it, and produce a plan to finish it: modern, secure, and production-ready. No code gets written until you approve this document. After that, work goes **one module at a time**, and each module waits for your review.

**Decisions you made (these shape the plan):**

| Question | Your answer | Effect on the plan |
|---|---|---|
| Missing `frontend/lib/` | Lost, rebuild it | Module 4 rebuilds the frontend data and auth layer from a generated, typed API client |
| Audience | Commercial SaaS | Strict tenant isolation (app checks plus Postgres RLS), Stripe billing, GDPR work, public marketing site |
| Scope | Focused core first | Core launch scope in §6.1. Other pillars move to post-launch Phase B |
| Hosting | Docker Compose on a VPS | Hardened single host, Caddy TLS, same-origin routing, encrypted off-site backups |
| **Search focus** | **Google first for classic SEO, other engines as add-ons, AI search as a second track** | Two first-class tracks (§1.1). Google gets the deepest coverage in every plan. Bing and regional engines are plan add-ons. The data model is engine-aware from day one (§4.5) |
| **Data independence** | "Can we build our own instead of relying on DataForSEO or SerpAPI?" | **Yes, for everything except fetching public search result pages.** We build the data engine ourselves: storage, parsing, metrics, history, and official-API integrations. Only the raw download of public SERPs is rented, from swappable vendors with automatic failover, so no single provider can lock us in. We don't run our own Google scraper at launch, for legal and technical reasons (§4.6) |

**Naming:** the code mixes "Voltex" and "SerpTank". We standardize on **SerpTank** everywhere (cookies, env, docs, UA string).

---

## 1. What SerpTank wants to be

It is a **multi-tenant SEO intelligence SaaS** that helps agencies and in-house teams **rank higher on Google**, extend that visibility to other search engines, and **get cited in AI-generated answers**. The code calls it an "SEO Decision Superiority Engine". The original pillars:

1. **Diagnose**: crawl sites, run technical and on-page audits, track Core Web Vitals.
2. **Monitor**: track keyword rankings, SERP features, and competitors. Pull Google Search Console and GA4 data.
3. **Monetize**: attribute organic revenue and ROI per page or keyword ("Profitability").
4. **Plan**: model what-if scenarios and market share ("Market Simulation").
5. **Produce**: create content briefs and optimization workflows ("Content Workflow").
6. **Future-proof**: prepare for AI search. The code calls this "SGE Readiness"; the market now calls it **GEO/AEO, or AI visibility** (AI Overviews, AI Mode, ChatGPT, Perplexity, Copilot).
7. **Remember**: keep a strategic ledger and a knowledge graph of past decisions ("Knowledge Engine").

### 1.1 Product positioning: two tracks, Google first

| Track | What it covers | Priority |
|---|---|---|
| **A. Classic search (primary)** | **Google**: technical health, indexing, keyword research, rankings, SERP features, on-page optimization, Core Web Vitals, and GSC/GA4 performance. **Other engines**: Bing (which also powers Yahoo and most DuckDuckGo results), then Yandex, Baidu, Naver, and Seznam for regional markets | Google is the backbone of every plan and gets the deepest feature set. Other engines are add-ons for customers who want the complete package |
| **B. AI search** | Google **AI Overviews and AI Mode**, ChatGPT search, Perplexity, Gemini, Microsoft Copilot, Claude: presence, citations, share of voice, and readiness | Core. Ships in the launch scope because AI answers now take a large share of queries |

The strategy: **one crawl, one keyword universe, one content model, measured across every engine.** Google data drives the recommendations. Other engines and AI answers appear as extra columns on the same keywords and pages, not as separate products.

**Engine coverage tiers** (what each plan level gets):

| Tier | Engines | Depth |
|---|---|---|
| **1: Google (all plans)** | Google Web (desktop and mobile, any country or city), plus Images, News, and Local pack as SERP features | Full: rank tracking, all SERP features (including AI Overview presence), GSC (performance, URL Inspection, sitemaps, and the Gen-AI report via CSV import until an API exists), CrUX Web Vitals, an audit built on Google Search Essentials, rich-result structured-data validation, on-page optimizer, keyword research |
| **2: Bing family (add-on or higher plans)** | Bing, plus Yahoo and DuckDuckGo (tracked as separate engines where the provider supports them) | Rank tracking, **Bing Webmaster Tools** integration (performance, crawl issues, URL submission), **IndexNow** instant indexing, Bing-specific audit checks (e.g. Bing honors `crawl-delay`; Google ignores it), Copilot citation data (Bing AI Performance: CSV import now, API when Microsoft ships it) |
| **3: Regional (add-on)** | Yandex, Baidu, Naver, Seznam | Rank tracking through the SERP provider. IndexNow pings (accepted by Yandex, Seznam, and Naver). Regional audit hints such as hreflang and local TLD signals |
| **AI search (all plans, with limits by plan)** | AI Overviews, AI Mode, ChatGPT, Perplexity, Gemini, Copilot, Claude | Presence and citation tracking, share of voice versus competitors, readiness scoring. Sampling volume scales with plan |

---

## 2. Phase 1 findings

### 2.1 Stack inventory (as found)

| Layer | Found |
|---|---|
| Backend | Python 3.12, FastAPI 0.116, Starlette 0.46, Pydantic 2.11, SQLAlchemy 2.0 async + asyncpg, Alembic (1 baseline migration, 53 tables), Celery 5.5 + Redis, Uvicorn |
| Auth | **Three parallel systems**: JWT (`/auth/*`, python-jose HS256), cookie sessions (`/auth/secure/*`, Redis), and a "migration" router. passlib/bcrypt |
| Data | PostgreSQL 15 **plus a separate** TimescaleDB container (the app never uses it), Redis 7, Weaviate 1.19 (anonymous access). Pinecone is also a dependency |
| ML/AI | OpenAI (`gpt-4` default), plus torch, transformers, sentence-transformers, spaCy (several GB of image weight) |
| Crawling | httpx, Playwright, Scrapy, Twisted, pyppeteer, BeautifulSoup, selectolax, lxml. Three overlapping stacks |
| Search data | SerpAPI wrappers (Google only; duplicated), GSC and GA4 through **global** credentials, PageSpeed Insights, pytrends. **No Bing, other engines, or keyword research data source** |
| Frontend | Next.js `^15.2.3`, React 19.1, Tailwind 3, Radix UI, TanStack Query 5, Zustand, axios, socket.io-client, Recharts 2. About 45 routes and 54 UI components |
| Infra | docker-compose dev and prod (Traefik), a k8s manifest, CI workflow at `backend/.github/` |
| Size | About 401 files and 114k lines. About 180 API routes in 31 endpoint modules. 33 service modules |

### 2.2 Blockers: the repo does not build or run as committed

1. **`frontend/lib/` is not in git.** The root `.gitignore` has a Python rule, `lib/`, that silently excluded 22 core modules: `api-client`, `auth-context`, `providers`, `utils`, `project-context`, `hooks/*`, and more. 249 imports across 115 files can't resolve, so the frontend cannot compile.
2. **The frontend has no Dockerfile**, although both compose files build one. There is also no `test/setup.ts`, which vitest's config expects.
3. **`backend/requirements.txt` is UTF-16** (a PowerShell `pip freeze`). It includes an unpinned `facebook_business`. pip handles UTF-16 badly.
4. **Config and env don't match.** `.env.example` sets `ADMIN_PASSWORD`, but the settings require `FIRST_SUPERUSER_PASSWORD` (case-sensitive), so the app won't start. Prod compose passes `DB_HOST/DB_NAME/DB_USER`, but the settings read `POSTGRES_*`. `SERPAPI_API_KEY` doesn't match `SERPAPI_KEY`.
5. **CI never runs.** The workflow lives in `backend/.github/` and not at the repo root. It calls Poetry, but there is no `pyproject.toml`. It runs Node 18, which is end-of-life.
6. **Backend tests can't run as written.** They use `sqlite+aiosqlite`, which is not installed and doesn't match the Postgres-specific schema.
7. **Realtime can never connect.** The frontend uses `socket.io-client`, but the backend serves a plain WebSocket that expects a JWT in the query string, which the cookie-session frontend doesn't have. This explains the "Disconnected" status in your Sept 2025 audit.
8. **Secure login probably never sets its cookie.** `auth/routes/auth_secure.py` sets cookies on the injected `Response` and then returns a *new* `JSONResponse`, which discards them. The frontend works around this by storing JWTs in `localStorage`.

### 2.3 Security audit (OWASP Top 10:2025 categories)

**Critical**

| # | Finding | Where | OWASP |
|---|---|---|---|
| C1 | **SSRF**: the crawler (httpx `follow_redirects=True` and headless Chromium) and user-configured webhooks fetch arbitrary URLs with no private-IP, loopback, or metadata blocking. Internal Redis (no password), anonymous Weaviate, and Postgres are all reachable | `services/crawler/http_client.py:128`, `services/crawler/engine.py`, `services/webhook_service.py:27` | A01 |
| C2 | **Cross-tenant data exposure by design**: integrations use one set of global server credentials (GA4 property, GSC site, social tokens), so every customer sees the operator's analytics and revenue | `services/google_analytics4.py:22,834`, `endpoints/profitability.py:647`, `endpoints/settings.py:211` | A01 |
| C3 | **Billing bypass**: any user can `POST /subscriptions/subscribe` for any plan with arbitrary `trial_days` and no payment. `/usage/track` is writable by users | `endpoints/subscriptions.py:162,302` | A01/A06 |
| C4 | **CORS reflection with credentials**: the `HTTPException` handler echoes any `Origin` with `Allow-Credentials: true` | `app/main.py:337-341` | A02 |
| C5 | **Bearer JWTs stored in `localStorage`** while the JWT login stays live, so any XSS means account takeover. This contradicts the documented cookie design | `frontend/app/login/page.tsx:86`, `auth/routes/auth.py` | A07 |

**High**

| # | Finding | Where |
|---|---|---|
| H1 | **Google OAuth login CSRF**: `state` comes from the client and is never verified. No PKCE or nonce. The `email_verified` claim is ignored. The error message discloses whether an account exists | `auth/routes/google.py:32-126`, `auth/services/google_auth.py:228` |
| H2 | **Authorization is ad hoc**: the tenant dependency is used in only 2 of 31 endpoint modules. The rest check `project.user_id == current_user.id`, which breaks team access and is easy to forget. Most tables are user-scoped instead of org-scoped | `core/tenant_dependencies.py`, `models/*` |
| H3 | **CSRF is broken**: two competing CSRF systems. The session validator accepts the CSRF *cookie* as the token, which defeats double-submit. Login, register, and logout are exempt. `HTTPException` raised inside `BaseHTTPMiddleware` becomes a 500 | `auth/core/session_security.py:332-336`, `core/csrf.py`, `main.py:213` |
| H4 | **Rate-limit bypass**: the client IP is taken from a spoofable `X-Forwarded-For` in three places, which defeats brute-force protection | `core/rate_limiter.py:165`, `core/rate_limit_dependencies.py:119`, `core/enhanced_rate_limiting.py:306` |
| H5 | **WebSocket auth**: the JWT goes in the query string (it ends up in logs), refresh tokens are accepted (no `type` check), there is no Origin check (cross-site WebSocket hijacking), and revocation is ignored. There is also an unauthenticated echo endpoint | `endpoints/websocket.py:25`, `endpoints/websocket_test.py` |
| H6 | **`pickle.loads` on Redis cache values**, while the session and blacklist clients ignore `REDIS_PASSWORD`. That is an RCE chain if Redis is reachable (see C1) | `core/cache.py:88-97`, `auth/core/session_security.py:47`, `auth/core/security.py:38` |
| H7 | **Crypto and secrets hygiene**: a deterministic hard-coded dev encryption key is used unless `ENVIRONMENT` is set (default: `development`). API keys are Fernet-encrypted under a unique index, so they can't be looked up and should be hashed instead. Password-reset tokens are stored in plaintext. Session IDs and emails are logged | `core/encryption.py:36`, `models/user.py:81`, `models/password_reset.py`, `session_security.py:196,257` |
| H8 | **Supply chain**: no frontend lockfile. `next ^15.2.3` with `react ^19.1.0` covers versions hit by **React2Shell (CVE-2025-55182, CVSS 10, RCE)**, and any build made before Dec 2025 was exploitable. python-jose has open CVEs (2024-33663/33664). passlib is unmaintained. urllib3 1.26, aiohttp, Starlette 0.46, and Authlib 1.6.0 all have later advisories |
| H9 | **Exposed internals**: `/metrics`, `/docs`, and `/openapi.json` are public. Flower is on :5555 with no auth. Postgres, Redis, and Weaviate ports are published to the host. Weaviate allows anonymous access. The Traefik container mounts `docker.sock` | `main.py:354-361`, `docker-compose.yml` |

**Medium and low**

- **M1**: 144 places return `str(e)` in HTTP error details, leaking internals (A10).
- **M2**: No security headers anywhere: no CSP, HSTS, `X-Content-Type-Options`, or `frame-ancestors`.
- **M3**: File uploads trust the client MIME type, allow SVG and ZIP up to 100 MB on local disk, and have no scanning.
- **M4**: Middleware order is inverted (CORS innermost). There is no session rotation on privilege change. Logout-all is a `SCAN` over every session. One `SECRET_KEY` is reused for JWT and CSRF.
- **M5**: The password policy uses composition rules (NIST 800-63B-4 disagrees). There is no breached-password check. MFA exists only as an unused column. Login timing reveals whether a user exists.
- **M6**: The Next.js middleware "verifies" auth by base64-decoding an unsigned JWT from a readable cookie.
- **M7**: **Fabricated data is shown to users**: fake `last_sync` times, placeholder "fallback" metrics when APIs fail, and billing invoices and usage that look invented (A08 integrity; bad trust and legal exposure for a SaaS).
- **L1**: Debug pages ship to production (`/auth-test`, `/design-showcase`, `page-old.tsx`), along with `console.log`s in the auth flow. `TRACE` is treated as a safe method. The repo contains PII: your email and account details in `COMPREHENSIVE_AUDIT_REPORT.md`.

### 2.4 Functional gap analysis

| Area | State today | Verdict |
|---|---|---|
| Auth / sessions / OAuth | Three overlapping systems, insecure (see above) | **Core**: rebuild (M3) |
| Orgs / projects / members / invitations | Partly works. "Sites" duplicates "Projects" | **Core**: consolidate Sites into Projects (M5) |
| Crawler / technical audit / CWV | Substantial logic, unsafe fetcher, three crawling stacks, rules not tied to Google's published guidelines | **Core**: port onto a safe client and rebase the rules on Google Search Essentials (M6) |
| **Indexing management** | None (no URL Inspection, sitemap submission, or IndexNow) | **Core**: GSC URL Inspection and sitemaps, Bing Webmaster Tools, IndexNow (M7) |
| **Keyword research** | None (only ad-hoc SerpAPI lookups) | **Core**: volume, difficulty, intent, SERP features, GSC "striking distance" opportunities (M8) |
| Rank tracking / SERP | Google-only SerpAPI wrappers (duplicated), no scheduling, TimescaleDB unused | **Core**: engine-aware tracking, Google first, Bing and regional engines as add-ons (M8) |
| **Multi-engine support** | None | **Core, as a plan add-on** (M7 Bing Webmaster Tools and IndexNow, M8 rankings) |
| GSC / GA4 / PageSpeed | Global credentials, 500s | **Core**: per-org OAuth connections, plus CrUX field data (M7) |
| **On-page optimization** | Scattered OpenAI prompts | **Core**: SERP-based page optimizer, keyword-to-page mapping, content briefs (M9) |
| SGE readiness | Heuristics tied to 2023's SGE | **Core, repositioned** as AI Visibility (GEO/AEO) across Google AI features and LLM answer engines (M10) |
| Dashboard / reports / notifications / realtime | UI exists. WS broken. Reports partial | **Core**: a unified "Search Presence" dashboard (M11) |
| Billing | Stripe router commented out. Self-serve plan grants | **Core**: Stripe plus server-side entitlements, including engine add-ons (M12) |
| **Backlink monitoring** | None | **Phase B #1** through a provider (a major Google ranking input) |
| **Local SEO (Google Business Profile)** | None | **Phase B** |
| Profitability (revenue attribution) | GA4 global-credential based | **Phase B**, after M7 |
| Content workflow (editorial calendar, assignments) | OpenAI prompts, 500s | **Phase B**. Briefs themselves move into core M9 |
| Knowledge engine | Weaviate/Pinecone, 500s | **Phase B** on pgvector |
| Market simulation | Heavy placeholders (29 mock/simulate markers) | **Phase B**: needs real data first |
| Google Trends | `pytrends`, archived Apr 2025, now broken | **Phase B** through a data provider (the official API is a gated alpha) |
| YouTube / social listening | X API is paid, tokens are global | **Phase B / optional**, through paid providers |
| Marketing / legal pages | Very large static pages, some fabricated content | **Core**: trim and rewrite honestly (M13) |

### 2.5 Engineering debt

- Duplicate modules: `notification.py`/`notification_service.py`, `activity`/`activity_service`, `google_trends`/`_service`, `serpapi`/`_service`, and shims for `crawler.py`, `openai_service.py`, `social_media.py`.
- Global service singletons that hold per-request state. Services use sync `Session` against an async engine (`password_reset_service.py`).
- Pages are huge (the analytics page is 3,234 lines, settings 1,935). The API client is hand-written with no generated types.
- Tests: about 3k lines, none runnable, with no frontend unit or e2e tests at all.
- Committed artifacts: `celerybeat-schedule`, the audit PDF and JSON, and an empty `ssl/` directory. `CLAUDE.md` describes a security model the code doesn't implement.

---

## 3. 2026 research summary (the basis for the choices below)

**Platform and security**

- **Next.js 16** is the Active LTS line (latest 16.2.x, supported to Oct 2027). React 19.2 is patched for React2Shell. Tailwind **v4** is stable (4.3.x). `next lint` is gone, so ESLint flat config is required. Node **24** is the current LTS.
- **FastAPI** now ships frequent releases (0.13x–0.14x). The official FastAPI docs replaced **passlib → pwdlib (Argon2id)** and **python-jose → PyJWT**. **uv** is the standard Python project and lockfile tool. **Ruff** replaces black, isort, and flake8.
- **OWASP Top 10:2025** (final Jan 2026) moves SSRF into A01 and adds **A03 Software Supply Chain Failures** and **A10 Mishandling of Exceptional Conditions**. This plan maps controls to it (§5.9).
- **Architecture:** a **modular monolith** (clear module boundaries, one deployable, one database) is the right fit for a single team and a VPS. Microservices would add operational cost with no benefit at this scale. The one exception is the browser renderer, which should be isolated for security.

**Search landscape**

- **Google** remains the primary target. Its public guidance, **Google Search Essentials** (technical requirements, spam policies, key best practices), is the rulebook the audit engine should encode.
  - In **June 2026 Google added a Generative AI performance report to Search Console**, covering AI Overviews and AI Mode impressions by page, country, and device. It is **UI/CSV only for now; the Search Console API does not expose it yet**, so we support CSV import now and switch to the API when Google ships it.
  - Google's May 2026 generative-search guidance says llms.txt and "content chunking" aren't needed. Readiness scoring should reward fundamentals.
- **Bing** matters beyond its own share: its index also powers **Yahoo, most DuckDuckGo results, and Microsoft Copilot grounding**.
  - **Bing Webmaster Tools** offers an API for site data and URL submission.
  - Since **Feb 2026 it has an AI Performance report** (Copilot citations and grounding queries, with intents, topics, and citation share added in June 2026). That report is CSV-only today, and Microsoft has said API access comes in 2026.
  - **IndexNow** (instant URL submission) is supported by Bing, Yandex, Seznam, and Naver. Google does not use it.
- **SERP data providers** such as **DataForSEO** and **SerpAPI** cover Google, Bing, Yahoo, Yandex, Baidu, Naver, and Seznam through one API. Multi-engine rank tracking needs no per-engine scraping.
- **Search data collection has become hard and legally risky:**
  - **Jan 2025:** Google Search started requiring JavaScript, which is widely read as a move against scrapers and SEO tools.
  - **Sept 2025:** Google removed `&num=100`, so the top 100 results now take 10 requests instead of 1.
  - **Dec 2025:** Google **sued SerpApi** for circumventing its "SearchGuard" anti-bot system. The court dismissed Google's DMCA claims in July 2026, but the case is ongoing and shows Google will litigate.
  - **Official search APIs are gone:** the **Bing Search APIs were retired on Aug 11, 2025**, and Google's **Custom Search JSON API is closed to new customers and ends Jan 1, 2027**. It never returned real ranked SERPs anyway.
- **Official data still available:**
  - The **Google Ads API Keyword Planner** gives search volume, CPC, and competition. It needs Basic Access, which since Sept 10, 2026 is granted per Google Cloud project, and volumes are only precise for accounts with ad spend.
  - The **Bing Webmaster Tools API** includes keyword research methods (`GetKeywordStats`, `GetRelatedKeywords`) and query and page stats with positions.
  - **GSC** gives real average positions for a site's own queries.
- **AI search:** GEO/AEO and AI-citation tracking (ChatGPT, Perplexity, Google AI Overviews and AI Mode, Copilot) is now standard across SEO suites. Classic search volume is down about 25% versus 2024.
- **Dead or restricted sources:** pytrends is dead, the Google Trends API is a gated alpha, and the X/Twitter API is paid. We use provider adapters (SERP, keyword, and trends data; PageSpeed Insights and CrUX for Web Vitals).

---

## 4. Architectural vision

### 4.1 Shape: a security-first modular monolith

```
                    Internet
                       │  TLS 1.3 · HSTS · HTTP/3
                 ┌─────▼─────┐
                 │   Caddy   │  one origin: app.serptank.com
                 └──┬─────┬──┘  /api/* → api      /* → web
          ┌─────────▼┐   ┌▼──────────┐
          │  web     │   │  api      │  FastAPI (stateless, N workers)
          │ Next 16  │   │  modules/ │──────────────┐
          └──────────┘   └──┬───┬────┘              │
                            │   │ enqueue           │
                   ┌────────▼┐ ┌▼──────────────┐ ┌──▼──────────────┐
                   │Postgres │ │ Redis (ACL)   │ │ workers (Celery)│
                   │17 + TSDB│ │ sessions,     │ │ queues: default,│
                   │+pgvector│ │ rate limits,  │ │ crawl, serp,    │
                   │  + RLS  │ │ broker, cache │ │ integr., ai,    │
                   └─────────┘ └───────────────┘ │ reports         │
                                                 └──┬──────────────┘
                                                    │ render jobs (internal RPC)
                                        ┌───────────▼───────────┐
                                        │ renderer (Playwright) │  isolated network,
                                        │ egress via filtering  │  no route to internal
                                        │ proxy (Smokescreen)   │  services
                                        └───────────────────────┘
   External data (all through SafeHttpClient + provider adapters, with per-org budgets):
   Google (GSC · GA4 · PSI/CrUX) · Bing Webmaster Tools · IndexNow ·
   SERP/keyword provider (Google, Bing, Yahoo, Yandex, Baidu, Naver, Seznam) · LLM APIs
```

- **Same-origin routing** (Caddy sends `/api/*` to FastAPI) removes CORS entirely and allows `__Host-` cookies with `SameSite=Lax`.
- **One Postgres cluster** with the TimescaleDB extension (rankings, visibility, and vitals hypertables) and pgvector (knowledge engine later). This drops the separate TimescaleDB container, Weaviate, and Pinecone.
- **Isolated renderer:** headless Chromium is the riskiest component. It runs in its own container with no route to Postgres or Redis, and outbound traffic goes through an SSRF-filtering proxy. Rendering is needed so audits see what Googlebot sees on JavaScript sites.

### 4.2 Backend layout (in place, `backend/`)

```
backend/
  pyproject.toml · uv.lock · alembic/ · tests/ (mirrors src)
  src/serptank/
    core/        config (fail-closed), logging (structlog + PII redaction), errors (RFC 9457),
                 db (async engine, tenant-scoped session, RLS GUC), redis, security primitives
                 (hashing, tokens, crypto keyring), http (SSRF-safe client), ratelimit, audit, otel
    modules/
      identity/      users, sessions, passwords, MFA (TOTP + passkeys), Google OIDC, API keys
      tenancy/       orgs, memberships, invitations, roles, policy engine
      projects/      projects (formerly "sites"), domain verification, target markets & engines
      crawler/       crawl orchestration, parser, robots, sitemaps, rendering client
      audit/         rule engine: Google Search Essentials rules + per-engine deltas; scoring
      integrations/  connection framework + gsc/, ga4/, psi_crux/, bing_wmt/, indexnow/
      search_data/   collector router (failover/pricing/cross-validation), vendor adapters,
                     OWN SERP parsers per engine, global public-SERP cache → SerpSnapshot / KeywordMetrics
      keywords/      keyword research, clustering, intent, keyword-to-page mapping
      rankings/      engine-aware tracking, SERP features, competitors, share of voice
      onpage/        page optimizer, SERP-based content briefs, internal-link suggestions
      ai_visibility/ AI Overview/AI Mode presence, LLM answer-engine sampling, citations, readiness
      llm/           provider-agnostic gateway (OpenAI adapter first), budgets, guards
      reports/       Search Presence dashboard data, PDF/CSV exports, scheduled email reports
      notifications/ in-app + email, alert rules, SSE stream
      billing/       Stripe checkout/portal/webhooks, plans, engine add-ons, entitlements, metering
    workers/     Celery app, queue routing, beat schedule
    main.py      app factory, middleware stack (ordered), router registration
```

Each module contains `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`, `tasks.py`, and `policies.py`. **import-linter** enforces the boundaries: a module talks to another only through its service interface or domain events, never through the other module's tables.

### 4.3 Frontend layout (`frontend/`)

- Next.js 16 App Router, TypeScript `strict`, pnpm, Tailwind 4. The existing Radix-based `components/ui/*` and layout components are kept.
- Route groups: `(marketing)`, `(auth)`, `(app)`. The **authoritative auth check runs server-side**: the `(app)/layout.tsx` server component calls `GET /api/v1/auth/session` with the forwarded cookie. `proxy.ts` (Next 16's replacement for middleware) only does cheap redirects and is never trusted.
- `lib/` is rebuilt: an **OpenAPI-generated typed client** (`openapi-typescript` + `openapi-fetch`), TanStack Query hooks per module, a CSRF header injector, a session provider, and SSE hooks. zod 4 plus react-hook-form for forms.
- **Engine-aware UI:** a global engine and market switcher shows Google by default. Tables and charts gain per-engine columns or series when add-on engines are enabled. AI visibility sits next to organic rank for the same keyword or page.
- **No fake data.** Every view has real loading, empty, error, "connect integration", and "upgrade to add engine" states.
- **Realtime uses Server-Sent Events** (cookie auth, one-way job progress and notifications). This is simpler and safer than WebSockets for this use.
- Big pages get split into feature folders under `features/<module>/`.

### 4.4 Background jobs

We keep Celery 5.5 (mature, already wired) with a Redis broker on its own ACL user.

- **Queues:** `default`, `crawl`, `render`, `serp`, `integrations`, `ai`, `reports`. Beat handles schedules such as rank checks, GSC and Bing syncs, and AI sampling.
- **Job state lives in a Postgres `jobs` table**, scoped to the tenant, so customers can see progress and audit history. Redis is not used as the result backend.
- Tasks are idempotent, with retries, exponential backoff, a dead-letter path, time limits, and per-org concurrency caps. The `serp` queue batches keywords per engine and locale to cut provider cost.

### 4.5 Search-engine coverage model (engine-aware by design)

- **`search_engine` is a first-class dimension**, not a hard-coded Google assumption. It is an enum: `google`, `bing`, `yahoo`, `duckduckgo`, `yandex`, `baidu`, `naver`, `seznam`.
  - A separate `ai_engine` enum covers `google_ai_overview`, `google_ai_mode`, `chatgpt`, `perplexity`, `gemini`, `copilot`, `claude`.
  - Every ranking, SERP snapshot, visibility metric, and alert carries `(engine, country, language, location, device)`.
- **Project targets:** each project declares its **target markets**, meaning country, language, optional city, and the engines tracked in each market. Google is on by default. Other engines toggle on only if the plan entitles them.
- **SerpTank's own data engine** (`search_data/`, see §4.6) normalizes every source into one schema:
  - `SerpSnapshot` holds organic results, SERP features, and any AI answer block with its citations.
  - `KeywordMetrics` holds volume, CPC, difficulty, intent, and trend.
  - Sources include official APIs, structured-JSON vendors, and raw HTML parsed by our own parsers.
  - Fetch vendors can be switched, mixed per engine, or failed over without touching feature code. A contract test suite runs against every adapter.
- **First-party data beats third-party data:**
  - Google data comes from GSC: real clicks and impressions, plus the Gen-AI report via CSV import until an API exists.
  - Bing data comes from Bing Webmaster Tools plus AI Performance (CSV now, API later).
  - Provider SERP checks fill the gaps and cover competitors.
- **Scoring:** a **Search Presence Score** per project and market blends share of voice per engine, weighted by the engine's market share in that country (configurable, Google-dominant by default), with AI citation share. Google is always shown first and can be viewed on its own.
- **Audit rules** encode Google Search Essentials as the baseline. Per-engine deltas are flagged separately, never as blanket "errors". Examples:
  - `crawl-delay` is honored by Bing but ignored by Google.
  - IndexNow applies to Bing, Yandex, Seznam, and Naver.
  - Baidu has specific requirements for hosting and simplified-Chinese content.

### 4.6 Search data independence: what we build and what we rent

**Goal:** SerpTank owns its data, logic, and history, and no single vendor can hold the product hostage. The only thing we rent is the one step that is legally risky and costly to run ourselves: **downloading public search result pages**.

```
 ┌──────────────── Layer 1: official & first-party APIs (we build the integrations) ─────────────┐
 │ GSC (real positions/clicks per query, page, country, device) · GSC URL Inspection · CrUX/PSI   │
 │ Bing Webmaster Tools (query/page positions + GetKeywordStats/GetRelatedKeywords)               │
 │ Google Ads API Keyword Planner (volume, CPC, competition) · IndexNow                          │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
 ┌──────────────── Layer 2: SerpTank data engine (we build and own all of it) ────────────────────┐
 │ Own SERP parsers per engine & SERP feature → normalized SerpSnapshot                          │
 │ Own snapshot history in TimescaleDB (if a vendor disappears, the history stays)                │
 │ Own metrics: keyword difficulty, intent, clustering, SERP volatility, share of voice,          │
 │   CTR curves (per tenant, from their GSC), Search Presence Score, opportunity finder           │
 │ Own crawler + renderer for ranking-page analysis (M6) · global public-SERP cache                │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
 ┌──────────────── Layer 3: raw public-SERP fetch (rented, commodity, swappable) ─────────────────┐
 │ Collector router → adapter A (e.g. DataForSEO) · adapter B (e.g. SerpAPI / Bright Data /       │
 │ Oxylabs) · "raw HTML" unblocker adapters parsed by OUR parsers · future self-hosted collector  │
 │ Failover, price-based routing, sample cross-validation between vendors, per-engine choice      │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Why we build Layers 1 and 2 ourselves:** this is where the product value lives. It is also cheap and legitimate, and it removes most paid calls:

- **Hybrid rank tracking.** For a customer's own site, daily positions come from **GSC and Bing Webmaster data at no cost**. Paid SERP fetches are used only for competitor positions, SERP-feature and AI Overview capture, keywords with no impressions yet, and exact-location checks, and they run at a plan-based frequency.
- **Global SERP cache.** Public SERPs are identical for everyone who searches the same query. If 50 customers track "best crm" for US desktop, we fetch it **once per day**. The cache stores only the public SERP, never which customers track it.
- **Own parsers.** "Raw HTML" collectors turn any generic unblocking or scraping vendor into a valid source. Switching vendors becomes a config change instead of a rewrite.
- **Own metrics.** Keyword difficulty, intent, clustering, and volatility are computed in-house from snapshots plus our own crawl of the ranking pages. We don't buy vendor scores.

**Why we don't run our own Google scraper at launch (honest assessment):**

1. **Legal.** Google's Terms prohibit automated querying, and Google is actively suing a SERP scraper. As a young commercial SaaS, scraping directly would put SerpTank itself in the line of fire. Buying from established providers moves most of the collection risk to vendors whose whole business is managing it.
2. **Technical.**
   - Google now requires JavaScript and runs SearchGuard, so every query needs a real headless browser.
   - The `num=100` removal means 10 page loads for a top-100 check.
   - Datacenter IPs, including our VPS, get blocked almost immediately, which forces paid residential proxy networks. Their sourcing ethics are often questionable.
   - City-level targeting needs proxies in each location.
   - Parsers break with every Google layout change (AI Overviews and AI Mode keep changing).
3. **Cost.** Headless browsers plus residential proxy bandwidth usually cost as much as or more than provider prices (around $0.60 per 1,000 SERPs at DataForSEO's standard queue), before counting engineering maintenance.
4. **Security.** A scraping fleet is a large attack surface. It would also get our IP ranges blacklisted, which would hurt our legitimate SerpTankBot crawler on customer sites.

**Kept open for later:** the collector interface lets us add a **self-hosted collector** as another adapter. It would start with engines that offer official paid APIs (for example the Yandex Cloud Search API) or where the terms allow it, and would cover Google only after a legal review (Phase C, §6.3).

---

## 5. Security architecture

### 5.1 Identity and authentication
- **Browser sessions (the only browser auth):** opaque 256-bit session ID in the cookie `__Host-st_session` (HttpOnly, Secure, SameSite=Lax, Path=/).
  - Redis stores the **SHA-256 of the ID**, so a Redis dump can't be replayed.
  - Idle timeout 24h, absolute timeout 14 days (30 with remember-me).
  - The ID **rotates on login, MFA, and privilege change**.
  - A per-user session index gives O(1) "log out all devices", and there is a device list UI.
- **Passwords:** Argon2id via `pwdlib`, at or above OWASP parameters. Legacy bcrypt hashes are verified and rehashed on login.
  - Minimum 12 characters (15 recommended), max 128, no composition rules.
  - Breached and common passwords are blocked through the HIBP k-anonymity range API.
- **MFA:**
  - TOTP (`pyotp`) with encrypted secrets and 10 hashed recovery codes.
  - **WebAuthn passkeys** (`webauthn` + `@simplewebauthn/browser`), usable as phishing-resistant MFA or for passwordless login.
  - Orgs can require MFA. Staff accounts must use it.
  - **Step-up re-auth** is required for email/password changes, API keys, billing, org deletion, and member role changes.
- **Sign in with Google:** OIDC Authorization Code with **PKCE S256, server-stored `state` and `nonce`** (Redis, 10-minute TTL, bound to a pre-auth cookie).
  - The ID token is validated (`iss`, `aud`, `exp`, `nonce`) with Authlib, and `email_verified` must be true.
  - Accounts are **never auto-merged by email**. Linking happens only from an authenticated session.
- **Brute force:** progressive delays plus per-account and per-IP counters, with Cloudflare Turnstile after a threshold. There are no hard lockouts, so an attacker can't lock users out. Login time is constant (a dummy hash is verified for unknown users). Responses are uniform so they don't reveal whether an account exists.
- **Email verification and password reset:** single-use 256-bit tokens stored **hashed** (reset tokens expire in 30 minutes). A successful reset revokes all sessions and sends a notification email.
- **Programmatic API:** **org-scoped API keys** in the form `stk_live_<prefix>_<secret>`. The database stores the prefix plus HMAC-SHA256(secret, server pepper). Keys have scopes, expiry, last-used tracking, and per-key rate limits. The legacy HS256 JWT login is **removed**. If JWTs are ever needed (service-to-service), they will use PyJWT with ES256/EdDSA, a `kid` for rotation, and pinned algorithms, and will validate `aud`, `iss`, and `exp`.

### 5.2 Authorization and tenant isolation
- **Org RBAC:** roles `owner`, `admin`, `editor`, `viewer`, `billing`. A permission matrix in code backs one `authorize(actor, action, resource)` policy function, and **every** router uses it through dependencies. Project-level restrictions are optional.
- **Tenant scoping, layer 1 (app):** every tenant-owned table has `organization_id NOT NULL`. The repository base class adds the tenant filter automatically. Cross-tenant lookups return **404**, not 403, so they don't reveal that the resource exists. IDs are UUIDv7, which can't be enumerated.
- **Tenant scoping, layer 2 (database, defense in depth):** **Postgres Row-Level Security** policies are keyed on `current_setting('app.org_id')`, which is set with `SET LOCAL` per transaction. The app's DB role is neither table owner nor `BYPASSRLS`. Migrations run as a separate owner role.
- **Provider cache isolation:** provider SERP snapshots can be cached globally (the same public SERP serves everyone) for cost reasons. **Tenant-specific data never enters that cache**: which keywords a customer tracks, their GSC/Bing data, and their competitor lists are always org-scoped.
- **Staff access** is a separate `platform_staff` flag. It requires MFA, and every staff action is audit-logged. Any future impersonation requires the customer's consent and is visibly logged in their audit trail.
- **Automated authz test matrix:** every endpoint is tested as every role and as a foreign tenant, and the expected status codes are generated from the policy table.

### 5.3 CSRF, CORS, and browser hardening
- **Same-origin deployment means no CORS.** A dev-only allowlist is used for local tooling.
- **CSRF:** a synchronizer token bound to the session, sent in the `X-CSRF-Token` header, **plus** checks on `Origin` and `Sec-Fetch-Site` for every unsafe method, including **login** (via a pre-session token). No path-prefix exemptions except the signature-verified Stripe webhook. Implemented as pure ASGI middleware that returns proper Problem Details responses.
- **Headers:**
  - Nonce-based **CSP**: `script-src 'nonce-…' 'strict-dynamic'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`.
  - HSTS (with preload once verified), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and COOP/CORP.
- Crawled HTML is **never rendered raw**. If a preview is needed, it goes into a sandboxed iframe with a separate origin.

### 5.4 Data protection
- **In transit:**
  - TLS 1.2+ (1.3 preferred) through Caddy's automatic certificates, with HTTP redirected to HTTPS.
  - Internal services are on a private Docker network with **no published ports**.
  - Managed-DB connections use `sslmode=verify-full`.
- **At rest:**
  - Encrypted VPS block storage.
  - **Encrypted off-site backups** (WAL-G or pgBackRest to S3-compatible object storage with object lock) and point-in-time recovery, with a restore drill every month.
  - **Application-level envelope encryption** (AES-256-GCM through `cryptography`, with a versioned keyring and `key_id` stored per record) for Google and Bing OAuth refresh tokens, IndexNow keys, TOTP secrets, webhook secrets, and provider API keys. A background job handles key rotation.
- **Secrets:**
  - `sops` + `age`-encrypted env files in the repo, decrypted in CI or at deploy and mounted as **Docker secrets** (files, not env vars).
  - Settings **fail closed** in production: a missing key stops the app from starting. Dev fallbacks apply only when `ENVIRONMENT=development` is set explicitly.
- **Keys** are separated by purpose: session pepper, CSRF key, API-key pepper, encryption KEK, and webhook signing. No single `SECRET_KEY` is used for everything.
- **Privacy (GDPR/CCPA):**
  - A data inventory, retention policies per plan, and self-serve **data export plus account and org deletion** (30-day grace, then hard delete).
  - A subprocessor list (including SERP and LLM providers), a DPA template, `security.txt`, and a vulnerability disclosure policy.

### 5.5 Input validation and SSRF defense
- Pydantic v2 models with `extra="forbid"`, strict types, length and size caps, and enum allowlists on every input (engines, locales, and devices included). SQL goes only through SQLAlchemy with bound parameters.
- **URL policy:** http/https only, no userinfo, IDNA-normalized, domains parsed with the Public Suffix List.
  - Domain ownership is verified before deep or scheduled crawls, and before any **IndexNow** or indexing submission. Verification uses DNS TXT or an HTML file, or is inherited from a verified GSC or Bing property.
  - Submitting URLs for sites you don't own is an abuse vector, so the ownership check is enforced.
- **`SafeHttpClient`** (all outbound fetches go through it):
  - Resolves DNS and **rejects private, loopback, link-local, CGNAT, multicast, reserved, ULA, and IPv4-mapped addresses**.
  - **Pins the resolved IP** so DNS rebinding can't swap it.
  - Re-checks every redirect hop (max 5).
  - Allows ports 80 and 443 only.
  - Caps response size and time and accepts only allowed content types.
  - The renderer adds a second egress filter. Webhooks use the same client, and their payloads are **HMAC-signed with a timestamp**.
- **Vendor SERP data is untrusted input:**
  - It is parsed with selectolax/lxml, with no network access and no entity resolution, and with size and time caps.
  - Parsers are fuzz-tested.
  - Cross-validation between vendors flags tampered or bad data before it is stored.
- **CSV imports** (GSC Gen-AI and Bing AI Performance exports, keyword lists):
  - Streamed and parsed with a size cap and a strict column schema.
  - Formula injection (cells starting with `=`, `+`, `-`, `@`) is neutralized in everything we later export to CSV.
- **File uploads (only where needed, e.g. logo or CSV import):**
  - The file type is sniffed from its magic bytes, and SVG is rejected unless sanitized.
  - Size caps apply.
  - Files go to object storage (S3-compatible) under random keys and are served as `attachment` from an isolated path.

### 5.6 Rate limiting, quotas, and abuse
- Redis GCRA/sliding-window limiter (Lua, atomic), applied by tier: per IP (anonymous), per user, per org, per API key.
  - Route classes: `auth` (for example 5/min and 30/h per IP+account), `expensive` (crawl, SERP batch, or AI sampling starts), `export`, and `general`.
  - Responses are `429` with `Retry-After` and `RateLimit` headers.
- **Correct client IP:** only Caddy is a trusted proxy (`--forwarded-allow-ips`). `X-Forwarded-For` is never read directly.
- **Plan entitlements are checked on the server** before any job is queued: crawl pages per month, tracked keywords **per engine**, engine add-ons, check frequency, AI prompts sampled, and seats.
- **Cost circuit breakers** protect paid external APIs (SERP, keywords, LLMs) with per-org and global daily budgets. Google and Bing API quotas are respected with backoff.
- **Our own crawler plays fair:** it identifies itself with a SerpTank UA, obeys robots.txt, and uses politeness delays, so we are never an abuse vector against customers' or competitors' sites.
- Optional: Cloudflare in front for DDoS and WAF.

### 5.7 Error handling, logging, and monitoring
- **RFC 9457 Problem Details** with stable error codes and a `trace_id`. Internal exception text never reaches clients (this fixes the 144 leaks). Authorization and validation paths **fail closed**. Every external call has a timeout and a circuit breaker. Job-creating and billing POSTs take **idempotency keys**.
- **Provider failures degrade honestly.** A failed SERP or API call marks that data point "unavailable, retrying"; it is never filled with a guess.
- `structlog` JSON logs with correlation IDs and a **redaction processor** (no tokens, session IDs, or secrets; emails hashed).
- **Append-only security audit log**, visible to org admins: logins, MFA changes, role changes, key creation, integration connections, exports, billing.
- **OpenTelemetry** traces and metrics, feeding Grafana/Prometheus/Loki (self-hosted) or Sentry for errors. Alerts fire on auth-failure spikes, logins from a new country, MFA disabled, 5xx rate, queue backlog, provider-budget burn, backup failure, and certificate expiry.

### 5.8 Supply chain and runtime
- Committed `uv.lock` and `pnpm-lock.yaml`. Renovate groups updates weekly. **pip-audit, pnpm audit, OSV-Scanner, Semgrep/Bandit, gitleaks, and Trivy** all run in CI, with a CycloneDX SBOM for each image.
- GitHub Actions are pinned by SHA with a least-privilege `GITHUB_TOKEN`. Base images are pinned by digest. Images are optionally signed with cosign.
- Containers run as non-root with a read-only root filesystem, `cap_drop: ALL`, `no-new-privileges`, and resource limits. No `docker.sock` mounts (Caddy replaces Traefik).
- **LLM safety (OWASP LLM Top 10):**
  - Crawled content and SERP snippets are untrusted data: they are delimited and never get tool or execution authority.
  - Outputs are schema-validated.
  - Per-org token budgets apply.
  - Nothing unnecessary is sent to model providers.

### 5.9 OWASP Top 10:2025 coverage map

| Risk | Primary controls | Module |
|---|---|---|
| A01 Broken Access Control (incl. SSRF) | Policy engine, tenant repo filter, **RLS**, 404-on-foreign, authz test matrix, SafeHttpClient, isolated renderer, ownership check before indexing submissions | M2, M3, M6, M7 |
| A02 Security Misconfiguration | Fail-closed settings, no public internals, security headers/CSP, same-origin (no CORS), hardened compose and host | M1, M14 |
| A03 Supply Chain Failures | Lockfiles, Renovate, audits, SBOM, pinned actions and images, gitleaks | M0 |
| A04 Cryptographic Failures | Argon2id, hashed tokens and keys, AES-GCM keyring and rotation, TLS 1.3, encrypted backups | M1, M3, M14 |
| A05 Injection | ORM-bound params, strict Pydantic, React escaping plus CSP, no raw HTML rendering, CSV formula neutralization | M1, M4, M11 |
| A06 Insecure Design | Threat model per module, server-side entitlements, Stripe-verified billing, idempotency, provider cost breakers | all, M8, M12 |
| A07 Authentication Failures | Sessions, MFA and passkeys, OIDC+PKCE, brute-force controls, step-up | M3 |
| A08 Data Integrity Failures | Signed webhooks (in and out), no pickle, no fake data, signed images | M1, M7, M12 |
| A09 Logging and Alerting Failures | Audit log, redacted structured logs, OTel, alerts | M1, M14 |
| A10 Exceptional Conditions | Problem Details, fail-closed, timeouts and circuit breakers, honest degradation | M1, M8 |

---

## 6. Modular implementation roadmap

### 6.1 How we'll work

- **Strategy: rebuild the foundation, port features.** Legacy code stays in place until the module that replaces it lands. That module's PR ports the good logic, deletes the old code, and adds tests. Git history is the archive.
- **One module = one PR** on `claude/laughing-archimedes-9woi38` (or a sub-branch per module if you prefer).
- **Each module ships with:**
  - Commented, modular code.
  - Strict error handling.
  - Unit and integration tests.
  - A short threat-model note in `docs/adr/`.
  - Passing CI.
- **I stop after each module for your approval.**
- **Core launch = M0–M14.** Phase B pillars come after launch.

| # | Module | Size | Depends on |
|---|---|---|---|
| M0 ✅ | Repo reset and toolchain | S | none |
| M1 ✅ | Platform core (config, errors, logging, DB/Redis, security middleware, SafeHttpClient) | M | M0 |
| M2 ✅ | Data model and multi-tenancy (fresh baseline schema, RLS, engine and market dimensions) | M | M1 |
| M3 ✅ | Identity and access (sessions, passwords, MFA/passkeys, Google OIDC, RBAC, API keys, audit) | L | M2 |
| M4 ✅ | Frontend foundation (rebuild `lib/`, generated client, auth UX, Next 16/Tailwind 4, engine switcher) | L | M3 |
| M5 ✅ | Orgs, projects, target markets, members, invitations (API + UI) | M | M4 |
| M6 ✅ | Jobs, crawler, and technical SEO audit (Google Search Essentials + engine deltas, Web Vitals) | L | M5 |
| M7 ✅ | Integrations and indexing: GSC (+URL Inspection, sitemaps, Gen-AI import), GA4, PSI/CrUX, Bing Webmaster Tools (+keyword API), Google Ads Keyword Planner, IndexNow | L | M5 |
| M8 ✅ | **SerpTank search data engine**: own parsers, collector router, SERP cache, own metrics, keyword research, hybrid engine-aware rank tracking (Google first; Bing family and regional as add-ons) | L | M7 |
| M9 ✅ | On-page optimization and SERP-based content briefs (Google-first) | M | M6, M8 |
| M10 ✅ | AI visibility (GEO/AEO) + LLM gateway | M | M8, M9 |
| M11 ✅ | Search Presence dashboard, reports and exports, notifications and alerts, SSE realtime | M | M6–M10 |
| M12 ✅ | Billing and entitlements (Stripe, plans, engine add-ons, metering) | M | M5 |
| M13 | Compliance, marketing site, legal | S | M12 |
| M14 | Production deployment and operations hardening | M | all |

### 6.2 Module details

**M0: Repo reset and toolchain**
- Fix `.gitignore`: scope the Python rules to `backend/` and un-ignore `frontend/lib/`.
- Remove committed artifacts: `celerybeat-schedule`, the audit PDF and JSON (PII), and the empty `ssl/` directory. Rewriting history to purge them is optional, and I'll ask first.
- Backend: `pyproject.toml` + `uv.lock` (Python 3.13, with a CI matrix that includes 3.14), ruff and mypy/pyright configs, pre-commit.
- Frontend: pnpm + lockfile, Node 24, ESLint flat config, Prettier, Vitest setup file, Dockerfiles.
- Root `.github/workflows/`: lint, typecheck, tests (Postgres and Redis service containers), pip-audit/pnpm audit/OSV/gitleaks/Semgrep/Trivy.
- `docker-compose.dev.yml`: services on a private network, one Postgres with TimescaleDB and pgvector, Redis with a password, no Weaviate.
- Rewrite `CLAUDE.md` to describe the real architecture and the Google-first two-track product, and standardize the name to SerpTank.
- *Exit:* CI is green on an empty-but-wired skeleton, `docker compose up` gives healthy services, and no secrets are found.

**M1: Platform core**
- `core/config`: pydantic-settings, fail-closed, secrets from files.
- Logging with structlog, redaction, and correlation IDs.
- RFC 9457 errors: global handlers, and no `str(e)` in responses.
- Async DB session factory with tenant GUC hook. A Redis client that honors auth and TLS. A crypto keyring (AES-GCM).
- **SafeHttpClient** with SSRF guard.
- Ordered ASGI middleware stack: proxy headers (trusted proxy only), security headers, request ID, CSRF, and rate limiting.
- `/healthz` (liveness) and `/readyz` (readiness). `/metrics` sits on an internal port only, and `/docs` is off in production.
- *Tests:* SSRF corpus (IPv4/IPv6/encodings/redirects/rebinding), header assertions, error-leak tests, config fail-closed tests.

**M2: Data model and multi-tenancy**
- New **baseline migration** replacing the old one, since there is no production data to preserve.
  - UUIDv7 primary keys. `organization_id NOT NULL` on every tenant table. `created_at` and `updated_at` columns. Soft-delete only where needed.
  - Sites merged into Projects.
  - **`search_engine` and `ai_engine` enums, and a `project_markets` table** (country, language, location, device, engines).
  - RLS policies with separate owner and app roles.
  - TimescaleDB hypertables for `rank_observations`, `visibility_daily`, `gsc_daily`, `bing_daily`, `ai_observations`, and `vitals`.
- A repository base class that scopes every query to the tenant.
- A seed script that generates a local dev superuser (no fixed default password).
- *Tests:* Postgres via testcontainers (not SQLite). **RLS tests prove that a query with a missing tenant filter still returns nothing across tenants.**

**M3: Identity and access**
- Everything in §5.1–5.2: register and login, email verification, reset, sessions and device management, TOTP plus recovery codes, **passkeys**, step-up auth, Google OIDC (PKCE/state/nonce), RBAC policy engine, org API keys, and the security audit log.
- Delete the JWT, auth-migration, and duplicate auth routers.
- *Tests:* unit tests for hashing, tokens, and policy. Integration tests for every flow. Negative tests for OAuth state/nonce replay, CSRF on login, session fixation, enumeration timing, and the brute-force ladder. The generated **authz matrix test**.

**M4: Frontend foundation**
- Next 16, React 19.2, Tailwind 4.
- Rebuild `lib/`: OpenAPI-generated client, TanStack Query setup, session provider, CSRF injection, SSE hook, `cn` utils.
- Server-side auth gate in `(app)/layout`. Screens for login, register, MFA, passkeys, reset, verify, and sessions.
- CSP nonces set via `proxy.ts`/headers.
- App shell with the **market/engine switcher** (Google default; locked engines show an upgrade state).
- Remove the debug pages, socket.io, and all fake fallback data. Honest empty and error states.
- *Tests:* Vitest + Testing Library + MSW. Playwright e2e for the auth flows. axe accessibility checks.

**M5: Orgs, projects, target markets, members**
- Org CRUD, invitations (hashed tokens, expiry, email), role management with a last-owner guard.
- Project CRUD with **target markets and engines** (entitlement-checked).
- Domain verification (DNS TXT or HTML file), plus the UI for all of it.
- *Tests:* authz matrix extended, invitation abuse cases (reuse, wrong email, expired), engine-entitlement enforcement.

**M6: Jobs, crawler, technical SEO audit**
- Celery queues plus the Postgres `jobs` table and SSE progress.
- Port `html_parser`, `robots_handler`, and `url_utils` onto SafeHttpClient: politeness delays, robots.txt evaluated **per bot** (Googlebot and Bingbot rules can differ), sitemaps, crawl budgets per plan.
- Isolated **renderer** service (Playwright) to compare raw HTML with rendered HTML, the way Google renders JavaScript.
- **Audit rule engine built on Google Search Essentials:**
  - Indexability: status codes, noindex, canonicals, robots, redirect chains, soft 404s, orphan pages.
  - Crawlability: internal linking depth, sitemap coverage, parameter and duplicate handling.
  - Mobile-first parity between mobile and desktop.
  - Page experience: Core Web Vitals through **PSI (lab) and CrUX (field)**, HTTPS, intrusive interstitials.
  - Structured data validated against Google rich-result requirements.
  - hreflang and international setup.
  - Titles, meta descriptions, and headings.
  - Spam-policy red flags: cloaking diffs between raw and rendered HTML, hidden text, doorway patterns.
- **Per-engine deltas** are flagged separately (Bing `crawl-delay`, IndexNow readiness, Baidu/Yandex regional hints).
- Priority scoring weighs the fix's impact against its effort, with Google impact weighted first.
- Delete Scrapy, Twisted, and pyppeteer.
- *Tests:* crawler against a local fixture site with known defects (a golden audit result). The SSRF suite runs through both the crawler and the renderer. A unit test for every rule.

**M7: Integrations and indexing**
- A `Connection` model per org: provider, scopes, encrypted tokens, health status, and last sync.
- **Google** (OAuth client separate from sign-in, incremental scopes):
  - GSC Search Analytics: queries, pages, countries, devices, and search appearance, synced daily into hypertables with backfill.
  - **URL Inspection** for index status and coverage.
  - **Sitemap submission** and status.
  - **Gen-AI performance report CSV import** (AI Overviews and AI Mode impressions), with an adapter ready for when Google adds it to the API.
  - GA4 organic landing-page engagement and conversions.
- **Bing Webmaster Tools** (API key or OAuth, as supported):
  - Site performance with query and page positions, crawl and index issues, URL submission.
  - **Keyword research API** (`GetKeywordStats`, `GetRelatedKeywords`): free Bing keyword impressions and ideas.
  - **AI Performance CSV import** (Copilot citations and grounding queries), with an adapter ready for Microsoft's promised API.
- **Google Ads API Keyword Planner** (official search volume, CPC, and competition):
  - **Apply for Basic Access for SerpTank's Google Cloud project at the start of M7**, since review takes time and the use case must pass Google's review.
  - Until approval, and as a fallback, volume comes from a rented keyword-data adapter. Volumes are precise only if the Ads account has spend; otherwise we store Google's ranges honestly.
- **IndexNow:** per-project key generation and hosting instructions (or DNS-verified), automatic pings for new or changed URLs found by the crawler or submitted by the user. Pings go only to verified domains.
- Quota-aware schedulers, token refresh and revocation handling, and a "connect" UI instead of fake data.
- *Tests:* recorded HTTP fixtures (respx/VCR) per API, token refresh and revocation, CSV parser fuzzing, tenant isolation of synced data, ownership enforcement for submissions.

**M8: SerpTank search data engine, keyword research, and rank tracking** (see §4.6)
- **Own data engine** (`search_data/`):
  - **SerpTank's own SERP parsers** per engine and SERP feature (organic, AI Overview with citations, featured snippet, PAA, local pack, video, images, shopping), tested against a versioned corpus of saved SERP HTML and JSON.
  - A normalized `SerpSnapshot` and `KeywordMetrics` schema.
  - **Snapshot history stored by us.**
  - A **global public-SERP cache** keyed by engine, keyword, locale, device, and date.
- **Collector router:**
  - At least **two interchangeable vendor adapters** (one structured-JSON vendor and one "raw HTML" unblocker parsed by our own parsers), with contract tests.
  - Automatic **failover**, price-based routing per engine, and **cross-validation** of a daily sample between vendors to catch bad data.
  - Budgets and circuit breakers. Switching vendors is a config change.
  - We start with the cheapest vendor that passes our quality tests, using the cost model in §9.
- **Keyword research, Google first:**
  - Volume and CPC from the **Google Ads Keyword Planner** (official, from M7) and the **Bing keyword API**, with the rented adapter as fallback.
  - **Difficulty, intent, and clustering computed by SerpTank** from SERP composition and our own crawl of the ranking pages.
  - SERP-feature presence, question and "People also ask" mining.
  - Related and long-tail expansion, keyword clustering by SERP overlap.
  - **Opportunity finder** from GSC data: "striking distance" queries at positions 8–20, and pages whose CTR is below what their position predicts.
- **Hybrid rank tracking:**
  - **The customer's own positions come daily and free from GSC and Bing Webmaster data.**
  - Paid SERP fetches, shared through the cache, cover competitors, SERP features, AI Overviews, zero-impression keywords, and exact-location checks.
  - Keyword sets per project and market. Paid-check schedules range from daily to weekly according to plan.
  - **Google desktop and mobile, local by city where needed.** Bing, Yahoo, DuckDuckGo, Yandex, Baidu, Naver, and Seznam when entitled.
  - Every SERP feature captured, including **AI Overview presence and cited URLs**. Competitor tracking and share of voice per engine.
  - The **engine market-share weighting** feeds the Search Presence Score.
- Merge GSC and Bing WMT data with tracked keywords (the real traffic view). Deduplicate the old `serpapi*` modules.
- *Tests:*
  - Parser tests against the saved-SERP corpus, with alerts when a real SERP fails to parse (a layout change).
  - Adapter contract tests. Router failover and cross-validation tests.
  - Cache-hit and tenant-isolation tests.
  - Hybrid-tracking merge tests (GSC position versus fetched position).
  - Scheduling, entitlement and cost caps, idempotent re-runs, and aggregation correctness with golden datasets.

**M9: On-page optimization and content briefs (Google-first)**
- **Keyword-to-page mapping**, with cannibalization detection (several pages competing for one query, using GSC and crawl data).
- **Page optimizer:** for a target keyword and market, compare the page against the current top-10 Google results.
  - Title, meta, and heading coverage.
  - Topic and entity coverage and content gaps.
  - Search-intent match.
  - Internal-link suggestions from the crawl graph.
  - Structured-data suggestions.
  - Readability and freshness.
  - Recommendations are **rule-based and explainable first**. Optional LLM rewrite suggestions go through the gateway, with budgets.
- **SERP-based content briefs** for new content: target and secondary keywords, intent, recommended outline from competitor headings and PAA questions, entities to cover, internal links, and schema type. Export to Markdown or Docs.
- The full editorial workflow (calendar, assignments, statuses) stays in Phase B.
- *Tests:* deterministic scoring on fixture SERPs and pages, LLM fakes, budget enforcement.

**M10: AI visibility (GEO/AEO)**
- **Google AI features:** AI Overview and AI Mode presence and citations from the SERP provider, plus GSC Gen-AI impressions (from M7).
- **LLM answer engines:** scheduled prompt sets per project and market against ChatGPT, Perplexity, Gemini, Copilot, and Claude (through APIs or providers). The OpenAI adapter comes first; others are added per budget. Bing AI Performance data (from M7) feeds Copilot.
- **Metrics:** brand mention rate, citation rate and cited URLs, share of voice versus competitors, and sentiment. Each is tracked **next to the organic rank for the same topic**.
- **Readiness score** built on fundamentals, following Google's May 2026 guidance: crawlable and indexable, helpful and original content, clear entities and brand signals, valid structured data, fresh facts, source-worthy formats.
- **LLM gateway:** model config, per-org budgets, prompt-injection guards, schema-validated outputs, and sampling statistics with confidence intervals (AI answers vary from run to run).
- *Tests:* deterministic LLM fakes, budget enforcement, injection test prompts, statistical aggregation tests.

**M11: Search Presence dashboard, reports, notifications**
- **Search Presence dashboard:** Google-first overview (GSC clicks, impressions, rank distribution, visibility), with engine tabs and AI visibility side by side. Also audit health, Web Vitals pass rate, and top opportunities.
- Report builder with PDF/CSV exports (async jobs, signed short-lived download URLs, CSV formula neutralization), scheduled email reports, and white-label options for agencies.
- In-app and email **alerts**: rank drops per engine, lost SERP features or AI citations, indexing regressions (URL Inspection or Bing), audit regressions, CWV failures. Delivered over an SSE stream.
- *Tests:* export authz, signed-URL expiry, alert rule evaluation, notification fan-out per tenant.

**M12: Billing and entitlements**
- Stripe Checkout, Customer Portal, and webhooks (signature-verified, idempotent event store).
- **Plans stored as data.** Google plus AI visibility is in every plan. **Engine add-ons**: Bing family, and regional engines. Limits cover keywords, check frequency, crawl pages, AI prompts, and seats.
- An **entitlement service** that every module checks. Usage metering. Dunning and grace-period handling.
- **Delete the self-serve `/subscribe` endpoint and the user-writable usage endpoint.** The billing UI shows only real invoices from Stripe.
- *Tests:* Stripe CLI and fixture events, replay and duplicate events, downgrade enforcement (engine add-on removal stops its tracking but keeps its history).

**M13: Compliance, marketing, legal**
- Trim the marketing pages to honest content: **remove fabricated case studies, testimonials, and stats**. Position the product as Google-first, all engines plus AI search.
- Pricing page generated from plan data (including engine add-ons). Rewrite the privacy policy, terms, and DPA, including the SERP and LLM subprocessors.
- Our own marketing site must pass our own audit. Cookie consent (only if non-essential cookies are added). Data export and deletion flows. `security.txt`.
- *Tests:* e2e for export and deletion. Lighthouse and accessibility budgets. A SerpTank audit of the marketing site with zero critical issues.

**M14: Production deployment and ops**
- Harden the VPS: Ubuntu 24.04 LTS, SSH keys only, no root login, nftables allowing 80/443 plus restricted 22, unattended-upgrades, CrowdSec.
- `docker-compose.prod.yml` with Caddy, api, web, workers, beat, renderer, Postgres, and Redis. Only Caddy publishes ports. Docker secrets for credentials.
- GitHub Actions builds images to GHCR, then deploys over SSH, with migrations as a one-shot job and a rollback path. Staging environment.
- Backups: WAL-G/pgBackRest to object storage with PITR, and a documented restore drill.
- Grafana/Loki/Prometheus or Sentry, uptime checks, provider-budget dashboards, alerting.
- **OWASP ZAP** baseline and full scans against staging. k6 load test (including a spike of rank-check jobs). Pre-launch security checklist. Incident-response and key-rotation runbooks.

### 6.3 Phase B (post-launch, in priority order)
1. **Backlink monitoring** through a provider: referring domains, new and lost links, anchor distribution, and competitor gap. A major Google ranking input.
2. **Local SEO**: Google Business Profile, local pack and map rank grids, citations (and Bing Places later).
3. Profitability / revenue attribution (GA4 per-org, keyword and page ROI).
4. Content workflow (editorial calendar, assignments, statuses) on top of M9 briefs.
5. Yandex Webmaster, Baidu Ziyuan, and Naver Search Advisor first-party integrations, if regional customers need them.
6. Knowledge engine on pgvector.
7. Google Trends via a provider.
8. Market simulation, once real ranking and traffic data exists.
9. YouTube and social listening through paid providers.

Each item follows the same module process.

**Phase C (optional, gated on a decision):** a **self-hosted SERP collector** as another adapter behind the router.

- It would start with engines that have official paid search APIs or permissive terms (for example the Yandex Cloud Search API).
- It would cover Google only after a **legal review** (the Terms of Service and the SerpApi litigation), and only if the cost model beats vendors.
- Because M8 already contains the parsers, router, and cache, this would add only the fetch layer.

### 6.4 Salvage map (what we port and what we delete)

- **Port and refactor:**
  - `services/crawler/{html_parser,robots_handler,url_utils}.py`
  - `services/core_web_vitals.py`, `pagespeed_insights.py`, `seo_analysis.py`, `diagnostic.py` (scoring)
  - GSC and GA4 client logic from `google_search_console.py` and `google_analytics4.py`, rewired to per-org credentials
  - Useful SerpAPI parsing from `serpapi*.py`, moved into the adapter
  - Concepts from `sge_readiness.py` (moved into M10)
  - Concepts from `multi_tenancy_service.py`
  - `frontend/components/ui/*` and `components/layout/*`
  - The CSRF and rate-limit test ideas
- **Delete:**
  - `auth/routes/{auth.py,auth_migration.py}`, `auth/main.py`
  - The duplicate `*_service.py` pairs and the shim modules
  - `websocket_test.py`, socket.io, `page-old.tsx`, `auth-test`, `design-showcase`
  - All placeholder and fallback data
  - Scrapy, pyppeteer, Weaviate, Pinecone, torch, transformers, spaCy

---

## 7. Dependency updates

### 7.1 Backend (`requirements.txt`, UTF-16, moves to `pyproject.toml` + `uv.lock`)

| Action | Packages | Reason |
|---|---|---|
| **Replace** | `python-jose` → `PyJWT` (only if JWT is needed) | Unmaintained, CVE-2024-33663/33664 |
| **Replace** | `passlib`/`bcrypt` → `pwdlib[argon2,bcrypt]` | Unmaintained, breaks on newer bcrypt and Python |
| **Replace** | `black`, `flake8`, `isort`, `pycodestyle`, `pyflakes`, `mccabe` → `ruff` | One fast tool |
| **Replace** | `requests`, `aiohttp`, `requests-oauthlib`, `httplib2` stack → `httpx` (via SafeHttpClient) | One async client, SSRF control. aiohttp 3.12.13 has later advisories |
| **Replace** | `google_search_results` (SerpAPI SDK) → thin httpx adapter in `search_data/` | Provider-agnostic, SSRF-safe, testable |
| **Replace** | `psycopg2` + `psycopg[binary]` duplicates → `asyncpg` (+ `psycopg` 3 only if sync is needed) | Duplicate drivers |
| **Replace** | `pendulum`, `pytz` → stdlib `zoneinfo`; `toml` → `tomllib` | Stdlib covers these |
| **Replace** | `pinecone*`, `weaviate-client` → `pgvector` (Phase B) | One database, less attack surface |
| **Replace** | `pytrends` → provider adapter (Phase B) | Archived Apr 2025, broken |
| **Remove** | `aioredis` (merged into `redis`), `fastapi-cache` + `fastapi-cache2` (duplicates, pickle) | Deprecated or duplicate |
| **Remove** | `torch`, `transformers`, `sentence-transformers`, `tokenizers`, `safetensors`, `huggingface-hub`, `spacy` (+`thinc`, `blis`, `cymem`, `preshed`, `srsly`, `wasabi`, `weasel`, `catalogue`, `confection`, `langcodes`, `murmurhash`, `spacy-*`), `scikit-learn`, `scipy`, `sympy`, `networkx`, `pyarrow`, `pandas`, `numpy` (unless a module proves a need, e.g. keyword clustering may keep `numpy`) | Several GB, unused by core. Embeddings via API if needed |
| **Remove** | `Scrapy`, `Twisted`, `pyppeteer`, `parsel`, `itemadapter`, `itemloaders`, `Protego`, `queuelib`, `w3lib`, `PyDispatcher`, `service-identity`, `zope.interface`, `Automat`, `constantly`, `hyperlink`, `incremental` | Replaced by httpx + selectolax + Playwright renderer (plus our own per-bot robots evaluator) |
| **Remove** | `tweepy`, `twython`, `facebook_business` (unpinned) | Phase B via providers |
| **Remove** (transitive or unused) | `pip-api`, `pip-requirements-parser`, `packageurl-python`, `cyclonedx-python-lib`, `license-expression`, `boolean.py`, `ecdsa`, `rsa`, `pyasn1*`, `python-slugify`, `yake`, `textstat`, `pyphen`, `cmudict`, `jellyfish`, `validators`, `tabulate`, `humanize`, `rich`, `typer`, `click-*`, `appdirs` | Either unused, or they come back pinned in the lockfile. The M9 readability metric gets a small maintained lib or its own code |
| **Move to dev group** | `pytest`, `pytest-asyncio`, `pytest-cov`, `coverage`, `mypy`, `pip_audit` + add `testcontainers`, `respx`, `schemathesis`, `hypothesis`, `import-linter`, `bandit` | Not in production images |
| **Update (latest stable, locked)** | `fastapi` (brings a patched `starlette`), `pydantic`, `pydantic-settings`, `SQLAlchemy` 2.x, `alembic`, `asyncpg`, `redis` 5+, `celery`, `uvicorn[standard]`, `Authlib`, `cryptography`, `openai`, `playwright`, `selectolax`, `lxml`, `beautifulsoup4`, `tldextract`, `email-validator`, `python-multipart` (≥0.0.18), `urllib3` 2.x, `prometheus-client`, `google-api-python-client`, `google-auth`, `google-analytics-data` | Security fixes and current APIs |
| **Add** | `structlog`, `opentelemetry-*`, `pyotp`, `webauthn`, `stripe`, `limits` (or own Lua), `uuid-utils` (UUIDv7), `publicsuffixlist`, `extruct` (structured-data extraction), `google-ads` (Keyword Planner), `sentry-sdk` (optional) | New capabilities |

`pip-audit` will run in M0 against the new lock to give an authoritative CVE list.

### 7.2 Frontend (`package.json`, adds `pnpm-lock.yaml`)

| Action | Packages |
|---|---|
| **Update (security-critical)** | `next` `^15.2.3` → **16.2.x** (LTS, includes the React2Shell and May-2026 fixes); `react`/`react-dom` → **19.2.x (patched)**; `eslint-config-next` → 16 |
| **Update (majors)** | `tailwindcss` 3 → **4** (+`@tailwindcss/postcss`, drop `autoprefixer`); `zod` 3 → 4; `date-fns` 3 → 4; `recharts` 2 → 3; `@hookform/resolvers` → latest for zod 4; `@types/node` → 24; `framer-motion` → `motion`; `lucide-react`, Radix, TanStack Query, `vitest`, `@playwright/test`, `typescript` → latest |
| **Remove** | `socket.io-client` (backend isn't socket.io; SSE replaces it), `axios` (use the generated `openapi-fetch` client), `critters` (deprecated) and `experimental.optimizeCss`, `modularizeImports`, the `images.domains` config (→ `remotePatterns`), `.eslintrc.json` (→ `eslint.config.mjs`) |
| **Add** | `openapi-typescript`, `openapi-fetch`, `@simplewebauthn/browser`, `@tanstack/react-table` (large keyword and ranking grids), `@testing-library/react` + `user-event` + `jest-dom`, `msw`, `@axe-core/playwright`, `server-only` |

### 7.3 Infrastructure

| From | To |
|---|---|
| Postgres 15 + separate TimescaleDB container | One **PostgreSQL 17** with TimescaleDB + pgvector |
| Weaviate 1.19 (anonymous) | Removed |
| Traefik v3 + `docker.sock` | **Caddy 2** (automatic TLS, no socket) |
| Redis 7, no auth | Redis 7.4+/Valkey with ACL users and no published port |
| Python 3.12 slim + Google Chrome in the API image | Python 3.13 slim API image without a browser. A separate Playwright renderer image |
| Node 18 CI | Node 24 LTS |
| `actions/*@v3` | Current major versions pinned by SHA |

---

## 8. Verification and definition of done (every module)

1. **Static checks:** `ruff check`, `ruff format --check`, `mypy --strict` (new code), `pnpm lint`, `pnpm typecheck`.
2. **Tests:** `uv run pytest` against real Postgres and Redis (testcontainers or CI services). At least 85% line coverage on new module code. `pnpm test` (Vitest). Playwright e2e for the module's user flows.
3. **External APIs** (Google, Bing, SERP providers, LLMs) are tested with recorded fixtures and contract tests. CI never calls paid APIs. An optional manual "live smoke" script runs with your keys.
4. **Security:**
   - Authz matrix and foreign-tenant tests.
   - Module-specific negative tests.
   - `schemathesis` fuzzing from OpenAPI.
   - pip-audit, pnpm audit, gitleaks, Semgrep, and Trivy clean (or explicitly waived in an ADR).
5. **Runtime check:** `docker compose up` and exercise the feature end to end in a browser (Playwright/Chromium available in this environment). No console errors, no fake data.
6. **Docs:** ADR plus a threat-model note, and an updated `CLAUDE.md` or README where behavior changed.
7. **Review gate:** I push the module, summarize the changes, list the test results, and **wait for your approval** before starting the next module.

---

## 9. Risks and open items

- **Choosing the SERP fetch vendors (before M8, low lock-in).** With our own parsers, router, and cache, no single choice is permanent. We start with the cheapest vendor that passes our quality tests (DataForSEO is pay-as-you-go at about $0.60 per 1,000 standard SERPs and covers every engine we need) plus a second, raw-HTML vendor for failover. Before M8 I'll bring a cost model per plan tier (keywords × engines × frequency × cache-hit rate × share covered free by GSC or Bing).
- **Google Ads API Basic Access might be refused.** Google reviews each use case, and since Sept 2026 access is granted per Google Cloud project. If it's refused, keyword volume comes from the rented keyword-data adapter. The product works either way.
- **Legal posture on SERP data.** We rely on vendors' own compliance for public-SERP collection and keep an eye on the Google v. SerpApi case. Phase C (self-hosted Google collection) stays off unless a lawyer approves it.
- **First-party AI data has no API yet.** Google's Gen-AI report and Bing's AI Performance report are UI/CSV-only today. We ship CSV import and switch to the APIs when they launch.
- **External API costs and quotas.** SERP and LLM providers are pay-per-use. M8–M10 include per-org budgets and global circuit breakers.
- **Google OAuth verification.** Sensitive and restricted scopes (GSC and GA4 read-only) require Google's app verification before public launch. Start the paperwork during M7.
- **Email provider** (Postmark, SES, or Resend) and **domain** (for SPF, DKIM, and DMARC) are needed by M3. I'll ask when we get there.
- **History purge.** Removing the committed PII and PDF from git history requires a force-push. It's optional and I'll only do it with your explicit OK.
- **Unreadable PDF.** I couldn't extract the review PDF's text (embedded fonts). If it holds decisions not reflected here, paste the key points.

---

### Sources
- [Next.js releases & support (endoflife.date)](https://endoflife.date/nextjs) · [Next.js support policy](https://nextjs.org/support-policy) · [Next.js May 2026 security release](https://vercel.com/changelog/next-js-may-2026-security-release)
- [React2Shell advisory (react.dev)](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components) · [Vercel CVE-2025-55182 summary](https://vercel.com/changelog/cve-2025-55182) · [GHSA-9qr9-h5gf-34mp](https://github.com/vercel/next.js/security/advisories/GHSA-9qr9-h5gf-34mp)
- [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) · [FastAPI OAuth2/JWT tutorial (pwdlib + PyJWT)](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) · [FastAPI PR #13917 (pwdlib/Argon2)](https://github.com/fastapi/fastapi/pull/13917) · [Introducing pwdlib](https://www.fvoron.com/blog/introducing-pwdlib-a-modern-password-hash-helper-for-python/)
- [OWASP Top 10:2025 introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/) · [Fastly: what changed in 2025](https://www.fastly.com/blog/new-2025-owasp-top-10-list-what-changed-what-you-need-to-know)
- [Tailwind CSS v4](https://tailwindcss.com/blog/tailwindcss-v4) · [Tailwind releases](https://github.com/tailwindlabs/tailwindcss/releases)
- [Google: Search Generative AI performance reports in Search Console (June 2026)](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports) · [GSC AI reports: what they track](https://crawlraven.com/blog/gsc-ai-performance-reports) · [Search Console AI visibility report details](https://www.elmohq.com/blog/search-console-ai-visibility)
- [Bing: Introducing AI Performance in Bing Webmaster Tools (Feb 2026)](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview) · [Bing: New AI visibility insights (June 2026)](https://blogs.bing.com/search/June-2026/New-AI-Visibility-Insights-in-Bing-Webmaster-Tools-Intents-Topics-Citation-Share-Compare) · [Bing AI Performance: is there an API? (Microsoft Q&A)](https://learn.microsoft.com/en-ca/answers/questions/5780844/bing-webmaster-tools-ai-performance-report-is-ther) · [Bing Webmaster Tools: setup, IndexNow and AI citations](https://gauravtiwari.org/bing-webmaster-tools/)
- [DataForSEO: supported search engines](https://dataforseo.com/help-center/search-engines-serp-api) · [DataForSEO SERP API docs](https://docs.dataforseo.com/v3/serp-overview/) · [DataForSEO SERP API pricing overview](https://nextgrowth.ai/dataforseo-serp-api/)
- [SEJ: Google files DMCA suit against SerpApi](https://www.searchenginejournal.com/google-files-dmca-suit-targeting-serpapis-serp-scraping/563847/) · [Search Engine Land: Google loses key DMCA claims against SerpApi](https://searchengineland.com/google-loses-key-dmca-claims-against-serpapi-in-scraping-lawsuit-483185) · [IPWatchdog on the complaint](https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/)
- [SEJ: Google requiring JavaScript to block SEO tools](https://www.searchenginejournal.com/confirmed-google-is-requiring-javascript-to-block-seo-tools/537705/) · [Search Engine Land: num=100 removal impact](https://searchengineland.com/google-num100-impact-data-462231)
- [Microsoft: Bing Search APIs retiring Aug 11, 2025](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement) · [Google Custom Search JSON API shutdown (Jan 2027)](https://keirolabs.cloud/blog/google-search-apis-2026)
- [Google Ads API developer token / access changes](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) · [PPC Land: developer tokens dropped from access decisions](https://ppc.land/google-drops-developer-tokens-from-ads-api-access-decisions/) · [Google Ads Developer Blog (Feb 2026)](https://ads-developers.googleblog.com/2026/02/an-update-on-google-ads-api-developer.html)
- [Bing Webmaster API: GetKeywordStats (Microsoft Learn)](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getkeywordstats?view=bing-webmaster-dotnet) · [GetRelatedKeywords](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getrelatedkeywords?view=bing-webmaster-dotnet)
- [pytrends (archived)](https://github.com/GeneralMills/pytrends) · [Does Google Trends have an API in 2026?](https://scrapebadger.com/blog/does-google-trends-have-an-api-what-to-use-in-2026)
- [Search Engine Land: What is GEO](https://searchengineland.com/what-is-generative-engine-optimization-geo-444418) · [AI SEO tracking tools 2026](https://www.searchinfluence.com/blog/ai-seo-tracking-tools-2026-analysis-platforms/) · [WRITER: GEO/AEO/SEO in 2026](https://writer.com/blog/geo-aeo-optimization/)
