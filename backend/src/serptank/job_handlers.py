"""Import every module that registers a job handler (API and workers both use this).

Lives outside ``serptank.core`` and ``serptank.modules.jobs`` because it depends on
feature modules.
"""

from serptank.modules.crawler import service as crawler_service  # noqa: F401 - registers "crawl"
from serptank.modules.integrations import sync as integration_sync  # noqa: F401 - syncs
from serptank.modules.keywords import ranks as keyword_ranks  # noqa: F401 - rank checks
