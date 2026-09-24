# ADR 0009: SerpTank search data engine, keyword research, rank tracking (Module 8)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M8

## Context

The owner asked for independence from SERP-data vendors (plan §4.6). We own storage, parsing, metrics and history. We rent only the raw fetch of public SERPs, and we keep that swappable.

## Decisions

1. **Normalized SERP model** (`search_data/schema.py`). Organic results, features, the AI answer with its cited URLs and domains, "People also ask", and related searches, for every engine.
   - DataForSEO JSON and our own HTML parsers both map onto this model.
   - Unknown vendor element types are kept as `other:<type>`, so a vendor change is visible rather than silently lost.
2. **Our own parsers:**
   - **Google:** anchored on semantic structure (`a[href] h3`, section headings, "AI Overview"). Ads are stripped and `/url?q=` redirects unwrapped.
   - **Bing** and **DuckDuckGo:** their own parsers.
   - **Parse failures:** a 200 page with no results and no "no results" message raises `SerpParseError`. The router then fails over and counts the failure; empty data is never stored.
   - **Corpus:** a versioned set of saved pages (`tests/search_data/corpus`). Add new layouts there.
3. **Collector router** (`search_data/collector.py`):
   - **Cache:** one global public-SERP cache per (engine, query, locale, device, day). It records nothing about which organization asked. Cache hits are free and uncounted.
   - **Adapters:** DataForSEO (JSON) and a generic raw-HTML "unblocker" (template URL, parsed by our parsers).
   - **Routing:** vendor order per engine, failover, and a per-process circuit breaker (5 failures opens it for 5 minutes).
   - **Cross-validation:** a sampled second-vendor fetch compares top-10 domain overlap (Jaccard) and stores the result in `serp_validations`.
   - **Budgets:** a global daily request cap across all orgs plus a per-org daily cap from the plan (free 100, pro 3,000, agency 30,000). When a budget runs out the answer is an honest "unavailable", never a guess.
   - **Accounting:** per-vendor usage and cost go to `vendor_usage`; per-org usage goes to `serp_usage` (RLS).
4. **Hybrid rank tracking** (`keywords/ranks.py`):
   - **Free first-party positions:** Google from GSC (impression-weighted over the last 7 days, filtered by market country and device) and Bing from Bing Webmaster Tools.
   - **Paid live checks, shared through the cache:** our position in the top 100, competitor positions, SERP features, and whether an AI answer cites us.
   - **Engines:** only entitled engines are checked. After a plan downgrade, history stays but new checks stop.
   - **Hypertable:** `rank_observations` stores readings from all sources side by side.
   - **Frequency:** from the plan (free weekly, paid daily) via beat.
5. **Our own metrics:**
   - **Intent:** rule-based, with its reasons shown. SERP features count as evidence.
   - **CTR curve:** fitted from the customer's own GSC data, with a public-average fallback that the UI names.
   - **Opportunities:**
     - "Striking distance": positions 8–20.
     - "Low CTR": CTR below half of what the position should earn.
   - **Share of voice:** CTR-weighted, volume-weighted where volumes exist. Otherwise keywords are weighted equally and the UI says so.
   - **Keyword difficulty v1:** an explainable 0–100 score. It reports its components and a confidence level based on cache size.

     | Component | Weight |
     |---|---|
     | Domain prominence across our cache | 45% |
     | Exact-match titles | 25% |
     | Homepages ranking | 15% |
     | SERP crowding | 15% |

     There is no backlink component until Phase B.
6. **Keyword research** from official sources only:
   - **Google Ads Keyword Planner:** exact volumes if the account has spend, otherwise ranges, stored as returned.
   - **Bing Webmaster Tools** related keywords (Bing impressions, labelled as such).
   - Without either, the API says what to connect.
   - "Analyze SERP" fetches (or reuses) the SERP and explains it.
7. **API and UI:** a Keywords page with four tabs:
   - **Rankings:** per market; Google first; the source of each position labelled; AI-cited badges; ">100" when we didn't rank in the checked depth.
   - **Research,** with SERP analysis.
   - **Opportunities.**
   - **Competitors and share of voice.**

## Cost model (per org per month, before cache sharing)

Assumptions: DataForSEO live at $0.002 per SERP (standard queue about $0.0006). Rank checks run at the plan's frequency. GSC and Bing cover the org's own positions at no cost, so the paid fetch buys competitors, features and AI answers.

| Plan | Keywords | Engines | Checks/month | Paid SERPs/month | Live cost | Standard queue |
|---|---|---|---|---|---|---|
| Free | 100 | Google | 4 (weekly) | 400 | $0.80 | $0.24 |
| Pro | 1,000 | Google + Bing family (≈2 fetches) | 30 | 60,000 | $120 | $36 |
| Agency | 5,000 | ≈3 engines | 30 | 450,000 | $900 | $270 |

The global cache lowers these costs. Head terms are shared across customers in the same locale. At a 30% hit rate, Pro drops to about $84 live or about $25 standard. Recommendations:

- Use the standard queue for scheduled checks, live only for on-demand "Analyze".
- Price Pro at or above $99 per month.
- Keep the per-org daily caps.

## Threat model notes

| Threat | Control |
|---|---|
| Cross-tenant leakage through the shared cache | The cache holds public SERPs only, with no org IDs. Tracked keywords, competitors and observations are RLS-scoped (tested) |
| Vendor returns bad or tampered data | Parse-failure detection, cross-vendor validation sampling, and vendor HTML parsed as untrusted data (no network, capped) |
| Runaway spend | Global and per-org daily caps, circuit breaker, cost accounting per vendor |
| Legal risk of scraping Google ourselves | Not done. We rent from vendors (§4.6), and self-hosted collection is Phase C, behind a legal review |

## Verified

- **Backend:** 350 pytest tests pass, with 91% coverage.
  - Parsers are tested against the saved corpus.
  - DataForSEO request shape and error mapping, and raw-HTML vendor URL and header auth, are tested over fake HTTP.
  - Router tests cover cache sharing across orgs, failover and the circuit breaker, both budgets, and cross-validation.
  - The hybrid tracking pipeline is tested end to end: first-party GSC position, live positions and competitors, AI-cited detection, and a zero-cost same-day re-check.
  - Also tested: share of voice, SERP analysis and difficulty, Bing-based research, opportunities, plan limits, budget exhaustion with an honest note, the scheduler, and tenant isolation.
  - Gates: ruff, mypy, import-linter, bandit and pip-audit are clean, with no OpenAPI drift.
- **Frontend:** 46 Vitest tests pass.
- **Playwright e2e (5 tests pass):** track keywords, then run a check with no vendor configured.

## Not verified here

- **Real vendor calls** (DataForSEO, an unblocker) and **live Google, Bing and DuckDuckGo markup.** The corpus pages are representative hand-made samples, not captured SERPs. Run `scripts_ci/live_smoke.py` with credentials, then add real captures to the corpus.
- **Keyword Planner** against a real Ads account (it needs Basic Access).
