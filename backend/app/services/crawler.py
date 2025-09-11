"""
Crawler service compatibility wrapper.

This module maintains backward compatibility by importing from the refactored crawler package.
The actual implementation has been moved to the crawler/ package for better organization.
"""
# Import from the refactored package
from .crawler import CrawlerService, crawler_service

# Re-export for backward compatibility
__all__ = ['CrawlerService', 'crawler_service']