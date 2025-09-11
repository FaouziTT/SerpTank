"""
Crawler service package.

This package provides web crawling functionality with support for
JavaScript rendering, robots.txt compliance, and comprehensive
link extraction and analysis.
"""
from .service import CrawlerService

# Create singleton instance for backward compatibility
crawler_service = CrawlerService()

__all__ = ['CrawlerService', 'crawler_service']