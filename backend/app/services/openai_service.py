"""
OpenAI service compatibility wrapper.

This module maintains backward compatibility by importing from the refactored openai package.
The actual implementation has been moved to the openai/ package for better organization.
"""
# Import from the refactored package
from .openai import OpenAIService, openai_service

# Re-export for backward compatibility
__all__ = ['OpenAIService', 'openai_service']