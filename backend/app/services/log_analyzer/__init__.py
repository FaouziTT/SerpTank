"""
Log analyzer service for the Diagnostic & Monitoring Core (Pillar 1).

This module provides services for analyzing log files from web servers,
CDNs, and other sources to gain insights about bot behavior and website usage.
"""

from .log_analyzer_service import LogAnalyzerService, log_analyzer_service

__all__ = ["LogAnalyzerService", "log_analyzer_service"]
