# ADR 0010: On-page optimizer, content briefs, keyword map, LLM gateway (Module 9)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M9

## Context

M9 turns M6 (crawl) and M8 (SERP data) into page-level advice: how one page compares with what ranks on Google for its keyword, what a new page should cover, which page should own each keyword, and where pages compete with each other. Optional AI rewrites need an LLM, so the provider-agnostic gateway that M10 extends is built here.

## Decisions

1. **Explainable, deterministic scoring first** (`onpage/analyzer.py`). Twelve checks, each with a weight, a status (`pass`, `warn`, `fail` or `info`), a message and a recommendation:
   - title, meta description, H1 and subheading keyword coverage;
   - the keyword in the first 100 words;
   - length against the median of ranking pages (with a note that length itself is not a ranking factor);
   - subtopic coverage;
   - page type against the competitors' dominant schema.org type;
   - structured data;
   - readability;
   - freshness;
   - image alt text;
   - internal inlinks from the latest crawl.
   The score is the weighted pass share (a warn counts half). Checks without evidence are `info` and don't move the score. This covers fewer than 3 readable competitors, no crawl, and non-English readability.
2. **Subtopics come from the ranking pages themselves.** We count unigrams and bigrams per page (with stop words for EN/DE/FR/ES) and keep terms that at least 40% of the readable top-10 pages use, excluding the keyword. We don't buy "NLP entities".
3. **Polite competitor reads** (`onpage/fetch.py`). Everything goes through `SafeHttpClient` with HTML-only responses, 2 MB and 15 s caps, at most 10 pages, 4 at a time and one per host.
   - `robots.txt` is honoured for SerpTankBot. A 5xx response means "don't fetch" (RFC 9309), and it gets its own reason.
   - Skipped pages are listed with the reason, never fetched around.
   - Only derived facts are stored (headings, counts, schema types). Competitor body text is never stored.
4. **Briefs** (`onpage/brief.py`):
   - **Outline:** competitor H2s grouped by Jaccard ≥ 0.5 on content words, keeping topics at least two pages cover, ordered by their typical position.
   - **Other sections:** People Also Ask plus question headings, shared terms, related searches, a length range (the middle half of ranking pages), a schema type (the dominant one, or a default for the intent), and internal link sources from the crawl.
   - **Missing evidence** is written into `notes` and never filled with guesses.
   - **Markdown export** escapes Markdown and HTML control characters in third-party text.
5. **Keyword map and cannibalization** (`onpage/mapping.py`):
   - **Keyword map:** each tracked keyword has an assigned target URL (it must be on the project's domain) and its latest own ranking URL for Google. The row is labelled aligned, mismatch, unassigned or not ranking.
   - **Cannibalization:** from GSC over 28 days. A query is flagged when it has at least 50 impressions and 2 or more pages each take at least 10% of them.
6. **LLM gateway** (`modules/llm/`):
   - **Providers:** providers sit behind a `LlmProvider` protocol, with OpenAI (Chat Completions plus JSON-schema response format) first and fakes in tests. Each call goes through its own `SafeHttpClient`.
   - **Budgets:** a per-org monthly token budget comes from the plan (`llm_tokens_per_month`: free 50k, pro 2M, agency 20M), plus a global kill switch (`SERPTANK_LLM_ENABLED`). Usage per purpose goes to `llm_usage` (RLS) and is shown at `GET /orgs/{org}/ai-usage`.
   - **Errors:** `LlmError` is an `AppError`, so it reaches clients as Problem Details: `llm_unavailable` 503, `llm_budget` 402, `llm_rate_limited` 429, `llm_invalid_output` 502. Provider exception text is never exposed.
7. **Jobs.** `page_optimize` and `content_brief` run on the `serp` queue. Their rows move from running to completed or failed, and a guard marks the row failed on *any* exception, so nothing is left "running".

## Threat model notes (OWASP Top 10:2025 plus the LLM Top 10)

| Threat | Control |
|---|---|
| Prompt injection from crawled or competitor text (LLM01) | Third-party text is sent only inside an `<untrusted>` block. The delimiter is neutralised inside it, and a system rule says to ignore instructions in data. The model has no tools, and its output is only displayed as suggestions |
| Insecure output handling (LLM05) | The output must validate against a Pydantic schema with length caps (`RewriteSuggestion`), or it is rejected. React escapes it on display |
| Unbounded consumption (LLM10) | Per-org monthly token budget, a rate limit on the rewrite endpoint (30/h), max output tokens, and a kill switch |
| Sensitive data sent to the provider (LLM02) | Only the page's title, meta, headings, keyword, subtopics and competitor titles are sent. No credentials and no user PII |
| SSRF via the optimizer URL | The URL must be on the project's domain, and every fetch goes through `SafeHttpClient` (a private-IP resolution is refused) |
| Abusive fetching of third-party sites | robots.txt honoured, one request per host per analysis, 10 pages max, analysis starts rate-limited (60/h) |
| Markdown or HTML injection in exported briefs | Control characters in third-party text are escaped. The export is served as an `attachment` with `no-store` |
| Cross-tenant access | All four new tables have `organization_id` with forced RLS. Foreign IDs return 404 (tested) |

## Verified

- **Backend:** 368 pytest tests pass, with 92% coverage and 83–99% on the new modules.
  - Analyzer, brief, outline and Markdown-escaping unit tests.
  - Gateway tests: metering, budget, invalid output, provider failure without leaking text, and the delimiter cannot be closed early.
  - OpenAI adapter request shape and error mapping, tested over fake HTTP.
  - API tests end to end:
    - the optimizer with a robots-blocked competitor, crawl-based link suggestions (a page that already links is excluded) and SERP position;
    - AI rewrite and the usage endpoint;
    - honest 503 without an LLM key;
    - failed-page recording;
    - brief and Markdown export;
    - a brief with no SERP available;
    - the keyword map with target assignment, domain validation and alignment after a rank check;
    - cannibalization from GSC;
    - cross-tenant 404.
  - Gates: ruff, mypy, import-linter, bandit and migration check are clean.
- **Frontend:** 49 Vitest tests pass.
- **Playwright e2e (5 tests pass):** the Content page empty states, then a brief created with no SERP vendor showing its honest notes.

## Not verified here

- Real OpenAI calls (they need a key). The request format follows the documented Chat Completions `response_format: json_schema`. Run a smoke test once a key is set.
- Scores on real sites and real SERPs. The weights are a considered first version and should be tuned against real rankings.
