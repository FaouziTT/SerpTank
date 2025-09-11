"""
Robots.txt handling for the crawler service.

This module provides functionality to check and respect robots.txt rules.
"""
import logging
from typing import Dict
from urllib.robotparser import RobotFileParser
from io import StringIO

import httpx

logger = logging.getLogger(__name__)


class RobotsHandler:
    """Handler for robots.txt files."""
    
    def __init__(self, user_agent: str = 'VoltexBot/1.0'):
        """
        Initialize the robots handler.
        
        Args:
            user_agent: The user agent string to use
        """
        self.user_agent = user_agent
        self._robots_cache: Dict[str, RobotFileParser] = {}
    
    async def check_robots_txt(self, domain: str) -> RobotFileParser:
        """
        Check robots.txt for the domain and cache the result.
        
        Args:
            domain: The domain to check robots.txt for
            
        Returns:
            RobotFileParser instance
        """
        if domain in self._robots_cache:
            return self._robots_cache[domain]
        
        rp = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    rp.set_url(robots_url)
                    # Use string IO to feed the content
                    rp.fp = StringIO(response.text)
                    rp.read()
                else:
                    # If robots.txt doesn't exist, allow all
                    rp.set_url(robots_url)
                    rp.fp = StringIO("User-agent: *\nAllow: /")
                    rp.read()
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            # On error, allow all
            rp.set_url(robots_url)
            rp.fp = StringIO("User-agent: *\nAllow: /")
            rp.read()
        
        self._robots_cache[domain] = rp
        return rp
    
    def can_fetch_url(self, robots_parser: RobotFileParser, url: str) -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            robots_parser: The RobotFileParser instance
            url: The URL to check
            
        Returns:
            True if the URL can be fetched, False otherwise
        """
        try:
            return robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            return True  # Allow on error
    
    def clear_cache(self):
        """Clear the robots.txt cache."""
        self._robots_cache.clear()
    
    def get_cache_size(self) -> int:
        """Get the number of cached robots.txt files."""
        return len(self._robots_cache)