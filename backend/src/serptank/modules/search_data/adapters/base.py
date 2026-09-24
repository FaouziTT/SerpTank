"""SERP collector adapter contract."""

from __future__ import annotations

from typing import Protocol

from serptank.modules.search_data.schema import SerpRequest, SerpSnapshotData


class CollectorError(Exception):
    """A fetch failed. ``message`` is safe to log; users see a generic 'unavailable'."""

    def __init__(self, vendor: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(f"{vendor}: {message}")
        self.vendor = vendor
        self.message = message
        self.retryable = retryable


class SerpAdapter(Protocol):
    name: str
    engines: frozenset[str]
    cost_micros: int

    async def fetch(self, request: SerpRequest) -> SerpSnapshotData: ...
