"""
Social Media Services Package.

This package provides integration with various social media platforms
for tracking brand mentions, social signals, and engagement metrics.
"""

from .twitter import TwitterClient
from .facebook import FacebookClient
from .linkedin import LinkedInClient
from .aggregator import SocialMediaAggregator

__all__ = [
    'TwitterClient',
    'FacebookClient', 
    'LinkedInClient',
    'SocialMediaAggregator'
]

# For backward compatibility
social_media_aggregator = SocialMediaAggregator()