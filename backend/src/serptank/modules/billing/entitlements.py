"""Plan entitlements - the single place that decides what a plan allows.

Enforced server-side before any work is queued (docs/execution-plan.md §5.6). The
frontend reads the same data to show upgrade prompts, but never decides.

Engine tiers (plan §1.1):
* Google is included in every plan.
* The Bing family (Bing, Yahoo, DuckDuckGo) is included from "pro".
* Regional engines (Yandex, Baidu, Naver, Seznam) are included in "agency".
Add-ons purchased separately (M12) extend a plan's engine set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from serptank.core.errors import AppError
from serptank.core.models import AIEngine, SearchEngine

BING_FAMILY = frozenset({SearchEngine.BING, SearchEngine.YAHOO, SearchEngine.DUCKDUCKGO})
REGIONAL = frozenset(
    {SearchEngine.YANDEX, SearchEngine.BAIDU, SearchEngine.NAVER, SearchEngine.SEZNAM}
)
GOOGLE_AI = frozenset({AIEngine.GOOGLE_AI_OVERVIEW, AIEngine.GOOGLE_AI_MODE})


class PlanLimitError(AppError):
    status = 402
    code = "plan_upgrade_required"
    title = "Your plan does not include this"


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    search_engines: frozenset[SearchEngine]
    ai_engines: frozenset[AIEngine]
    max_projects: int
    max_markets_per_project: int
    max_members: int
    max_tracked_keywords: int
    max_crawl_pages_per_month: int
    ai_prompts_per_month: int
    rank_check_interval_hours: int
    serp_requests_per_day: int = 0  # paid (uncached) SERP fetches per org per day
    llm_tokens_per_month: int = 0  # LLM input+output tokens per org per month
    addons: frozenset[str] = field(default_factory=frozenset)


PLANS: dict[str, Plan] = {
    "free": Plan(
        code="free",
        name="Free",
        search_engines=frozenset({SearchEngine.GOOGLE}),
        ai_engines=GOOGLE_AI,
        max_projects=1,
        max_markets_per_project=1,
        max_members=2,
        max_tracked_keywords=50,
        max_crawl_pages_per_month=500,
        ai_prompts_per_month=50,
        rank_check_interval_hours=168,
        serp_requests_per_day=100,
        llm_tokens_per_month=50_000,
    ),
    "pro": Plan(
        code="pro",
        name="Pro",
        search_engines=frozenset({SearchEngine.GOOGLE}) | BING_FAMILY,
        ai_engines=frozenset(AIEngine),
        max_projects=10,
        max_markets_per_project=5,
        max_members=10,
        max_tracked_keywords=1_000,
        max_crawl_pages_per_month=50_000,
        ai_prompts_per_month=2_000,
        rank_check_interval_hours=24,
        serp_requests_per_day=3_000,
        llm_tokens_per_month=2_000_000,
    ),
    "agency": Plan(
        code="agency",
        name="Agency",
        search_engines=frozenset(SearchEngine),
        ai_engines=frozenset(AIEngine),
        max_projects=100,
        max_markets_per_project=25,
        max_members=50,
        max_tracked_keywords=10_000,
        max_crawl_pages_per_month=500_000,
        ai_prompts_per_month=20_000,
        rank_check_interval_hours=24,
        serp_requests_per_day=30_000,
        llm_tokens_per_month=20_000_000,
    ),
}


def plan_for(code: str, addons: frozenset[str] = frozenset()) -> Plan:
    """Resolve a plan (unknown codes fall back to the most restrictive plan)."""
    base = PLANS.get(code, PLANS["free"])
    engines = set(base.search_engines)
    if "engines_bing" in addons:
        engines |= BING_FAMILY
    if "engines_regional" in addons:
        engines |= REGIONAL
    return Plan(**{**base.__dict__, "search_engines": frozenset(engines), "addons": addons})


def require_engines(plan: Plan, search: list[SearchEngine], ai: list[AIEngine]) -> None:
    missing = sorted({e.value for e in search} - {e.value for e in plan.search_engines})
    missing += sorted({e.value for e in ai} - {e.value for e in plan.ai_engines})
    if missing:
        raise PlanLimitError(
            f"Your {plan.name} plan does not include: {', '.join(missing)}.",
            extra={"missing": missing},
        )


def require_below_limit(current: int, limit: int, what: str, plan: Plan) -> None:
    if current >= limit:
        raise PlanLimitError(
            f"Your {plan.name} plan allows up to {limit} {what}.",
            extra={"limit": limit, "resource": what},
        )
