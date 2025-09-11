"""
Social Media APIs Integration.

This module provides integration with various social media APIs to fetch
social signals, brand mentions, and engagement metrics.

This is a compatibility wrapper that imports from the refactored social_media package.
"""
# Import all classes from the refactored package
from .social_media import (
    TwitterClient,
    FacebookClient,
    LinkedInClient,
    SocialMediaAggregator,
    social_media_aggregator
)

# Re-export for backward compatibility
__all__ = [
    'TwitterClient',
    'FacebookClient',
    'LinkedInClient',
    'SocialMediaAggregator',
    'social_media_aggregator'
]