# ADR 0011: AI visibility, GEO/AEO (Module 10)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M10

## Context

Track B of the product (plan §1.1): how often AI answers (Google AI Overviews, ChatGPT, Perplexity and others) mention and cite a customer, next to their organic rank for the same topic. We also need to report whether the site is ready to be cited.

## Decisions

1. **Prompt sets per project and market** (`ai_prompts`). Each prompt can be linked to a tracked keyword, so organic position sits beside AI presence. Duplicates are case-insensitive, with at most 200 prompts per project. Deterministic prompt suggestions are built from tracked keywords and intent, with no LLM and no cost.
2. **Sources, all through official channels or our collector:**
   - **Google AI Overviews:** the Google SERP for the prompt, fetched through the M8 collector. This is shared, cached and budgeted per day. We record whether an AI Overview was shown, and whether it names or cites the brand.
   - **ChatGPT:** the OpenAI Responses API with the `web_search` tool and approximate user location. Citations come from `url_citation` annotations.
   - **Perplexity:** the Sonar API, reading `citations` and `search_results`.
   - **Gemini, Copilot, Claude and Google AI Mode:** no sampling adapter yet. The UI shows them as *not available*, with the reason. Copilot citations come from the Bing AI Performance import (M7); AI Mode and AI Overview impressions come from the Search Console Gen-AI import.
   - The customer's prompt is sent as-is, with no system prompt, so we measure the answer a user would actually see.
3. **Sampling statistics.** Answers vary between runs, so each prompt is sampled `samples_per_prompt` times (1–10, default 3). Rates are always shown as `rate (low–high, n)` with a Wilson 95% interval, never a bare percentage.
4. **Detection** (`detect.py`). Brand matching is case-insensitive on word boundaries, over the domain, its label and configurable brand terms. Citations match the host (domain or `www` twin), and the check is reused for tracked competitors, which gives share of voice. We also record the mention rank (the brand's position among the brands named). Sentiment is a small lexicon heuristic over the sentences that mention the brand, and the UI labels it as a heuristic. We store only an excerpt of at most 600 characters around the mention, plus the cited URLs, never the full answer.
5. **Budgets and entitlements:**
   - An engine runs only if all of these hold: it is selected in the market, the plan includes it (free: Google AI surfaces only), and the server can sample it.
   - Each LLM sample counts toward `ai_prompts_per_month` (tracked in `llm_usage` with purpose `ai_sampling:<engine>`) and toward the monthly LLM token budget.
   - When either budget runs out, the job stops and returns a note.
   - A rate-limited engine is skipped for the rest of the run.
   - Re-running on the same day replaces that day's samples.
   - A weekly beat job samples every project that has active prompts.
6. **Readiness** (`readiness.py`) scores fundamentals only, following Google's May 2026 guidance (no llms.txt or "chunking" points). It is computed from the latest crawl and its audit issues:
   - **Access:** Googlebot and Bingbot reach the homepage, and AI *search* bots are not blocked. The crawler now records `ai_bots_allowed` for OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, GPTBot, Google-Extended, ClaudeBot and CCBot. Blocking training bots is reported but not penalised.
   - **The other components:** indexable share, content readable without JavaScript, Organization/WebSite schema and structured-data errors, thin or duplicate content, and page experience.

## Threat model notes

| Threat | Control |
|---|---|
| Answer text containing injected HTML or script | Answers are untrusted data. We store an excerpt and URLs only, and React renders them as text. Answers never reach another model or any tool |
| Runaway spend | Monthly sample cap and token budget per org, rate-limited manual runs (20/h), a weekly schedule, the global kill switch `SERPTANK_LLM_ENABLED`, and a cap on samples per prompt |
| Fabricated or over-precise metrics | Wilson intervals with n, "not available" instead of zeros for missing engines, and an empty state until something is sampled. Sentiment is labelled a heuristic |
| Cross-tenant leakage | `ai_profiles`, `ai_prompts` and the `ai_observations` hypertable have forced RLS. Foreign IDs return 404 (tested). The SERP cache shares only public SERPs |
| SSRF through provider calls | Provider calls go only to fixed API hosts, through `SafeHttpClient` |

## Verified

- **Backend:** 379 pytest tests pass, with 92% coverage.
  - Unit tests: detection (word boundaries, citations, rank, sentiment), Wilson values, prompt suggestions, and the OpenAI and Perplexity adapters over fake HTTP (request shape, citation extraction, 429 mapping).
  - API tests end to end:
    - settings, engine status and prompt CRUD;
    - a run over Google AIO plus two answer engines, with visibility intervals, share of voice with a competitor, and evidence;
    - same-day re-run replacement, pausing and cross-tenant 404;
    - a free-plan downgrade that limits engines, and monthly budget exhaustion with a note;
    - readiness from a crawl, first-party AI imports, and the weekly scheduler.
  - Gates: ruff, mypy, import-linter, bandit and pip-audit are clean, the migration round-trips, and `alembic check` is clean.
- **Frontend:** 53 Vitest tests pass.
- **Playwright e2e (5 tests pass):** the AI page empty states, adding a prompt, a run with no engines configured reporting "0 answers sampled", and readiness asking for an audit.

## Not verified here

- Live OpenAI Responses and Perplexity calls (they need keys). The request formats follow the published APIs; smoke-test them once keys are set.
- Real AI Overview markup, which depends on the M8 vendor captures.
- The Celery `ai` queue. M14's worker command must consume `default,crawl,serp,integrations,ai,reports`.
