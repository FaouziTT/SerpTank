"""Manual live smoke test for paid/external providers. Never run in CI.

Spends real (small) money. Run with production-like credentials in the environment:

    SERPTANK_DATAFORSEO_LOGIN=... SERPTANK_DATAFORSEO_PASSWORD=... \\
    SERPTANK_RAWHTML_ENDPOINT='https://vendor.example/?api_key={key}&url={url}' \\
    SERPTANK_RAWHTML_API_KEY=... SERPTANK_GOOGLE_API_KEY=... \\
    uv run python scripts_ci/live_smoke.py "best running shoes" US en

Each configured vendor fetches one SERP; our parsers/mappers must return organic
results. CrUX is queried for google.com. Output is a short pass/fail report.
"""

from __future__ import annotations

import asyncio
import sys

from serptank.core.config import Settings
from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.crux import CruxClient
from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.factory import build_router
from serptank.modules.search_data.schema import SerpRequest


async def main(query: str, country: str, language: str) -> int:
    settings = Settings()
    failures = 0
    async with SafeHttpClient() as http:
        router = build_router(settings, http)
        if not router.adapters:
            print("No SERP vendor configured.")  # noqa: T201
        for name, adapter in router.adapters.items():
            for engine in sorted(adapter.engines & {"google", "bing"}):
                request = SerpRequest(
                    engine=engine, query=query, country=country, language=language
                )
                try:
                    snapshot = await adapter.fetch(request)
                except CollectorError as exc:
                    failures += 1
                    print(f"FAIL {name}/{engine}: {exc.message}")  # noqa: T201
                    continue
                ok = bool(snapshot.organic)
                failures += not ok
                top = ", ".join(r.domain for r in snapshot.organic[:3])
                status = "OK  " if ok else "FAIL"
                print(  # noqa: T201
                    f"{status} {name}/{engine}: {len(snapshot.organic)} results; "
                    f"top: {top}; features: {snapshot.features}"
                )
        key = settings.google_api_key.get_secret_value()
        if key:
            vitals = await CruxClient(http, key).query(origin="https://www.google.com")
            print(f"{'OK  ' if vitals else 'FAIL'} crux: {vitals.values if vitals else 'no data'}")  # noqa: T201
            failures += vitals is None
    return 1 if failures else 0


if __name__ == "__main__":
    args = sys.argv[1:] or ["best running shoes", "US", "en"]
    sys.exit(asyncio.run(main(*args[:3])))
