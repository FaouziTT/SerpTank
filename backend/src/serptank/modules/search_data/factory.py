"""Build the collector router from settings (vendors without credentials are skipped)."""

from __future__ import annotations

from serptank.core.config import Settings
from serptank.core.http import EgressPolicy, SafeHttpClient
from serptank.modules.search_data.adapters.base import SerpAdapter
from serptank.modules.search_data.adapters.dataforseo import DataForSeoAdapter
from serptank.modules.search_data.adapters.rawhtml import RawHtmlAdapter
from serptank.modules.search_data.collector import CollectorRouter, parse_order


def build_router(settings: Settings, http: SafeHttpClient) -> CollectorRouter:
    adapters: dict[str, SerpAdapter] = {}
    if settings.dataforseo_login and settings.dataforseo_password.get_secret_value():
        adapters["dataforseo"] = DataForSeoAdapter(
            http,
            settings.dataforseo_login,
            settings.dataforseo_password.get_secret_value(),
            settings.dataforseo_cost_micros,
        )
    if settings.rawhtml_endpoint and settings.rawhtml_api_key.get_secret_value():
        adapters["rawhtml"] = RawHtmlAdapter(
            http,
            settings.rawhtml_endpoint,
            settings.rawhtml_api_key.get_secret_value(),
            settings.rawhtml_cost_micros,
        )
    return CollectorRouter(
        adapters=adapters,
        order=parse_order(settings.serp_vendor_order),
        global_daily_requests=settings.serp_global_daily_requests,
        cache_days=settings.serp_cache_days,
        validation_rate=settings.serp_validation_rate,
    )


def default_policy() -> EgressPolicy:
    return EgressPolicy()
