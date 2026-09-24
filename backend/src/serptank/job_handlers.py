"""Import every module that registers a job handler (API and workers both use this).

Lives outside ``serptank.core`` and ``serptank.modules.jobs`` because it depends on
feature modules.
"""

from serptank.modules.crawler import service as crawler_service  # noqa: F401 - registers "crawl"
