from __future__ import annotations

from serptank.core.models import uuid7


def test_uuid7_is_version_7_and_time_ordered() -> None:
    ids = [uuid7() for _ in range(50)]
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)
