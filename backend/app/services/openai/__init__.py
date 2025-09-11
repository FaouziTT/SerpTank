"""
OpenAI service package.

This package provides integration with OpenAI's API for content generation,
SEO optimization, and AI-powered insights.
"""
from .service import OpenAIService

# Create singleton instance for backward compatibility
openai_service = OpenAIService()

__all__ = ['OpenAIService', 'openai_service']