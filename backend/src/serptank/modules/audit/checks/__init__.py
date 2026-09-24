"""Importing this package registers every audit rule."""

from serptank.modules.audit.checks import (  # noqa: F401
    content,
    crawlability,
    engines,
    indexability,
    international,
    page_experience,
    rendering,
    spam,
    structured_data,
)
