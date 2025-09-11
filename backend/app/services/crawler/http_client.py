"""
HTTP client for the crawler service.

This module provides HTTP request handling with support for
both regular requests and JavaScript rendering using Playwright.
"""
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

import httpx
from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    status_code: int
    content_type: Optional[str]
    content: str
    title: Optional[str]
    error: Optional[str] = None


class HttpClient:
    """HTTP client for crawling web pages."""
    
    def __init__(self, user_agent: str = 'VoltexBot/1.0'):
        """
        Initialize the HTTP client.
        
        Args:
            user_agent: The user agent string to use
        """
        self.user_agent = user_agent
    
    async def fetch_with_playwright(self, url: str) -> CrawlResult:
        """
        Fetch a URL using Playwright for JavaScript rendering.
        
        Args:
            url: The URL to fetch
            
        Returns:
            CrawlResult with the fetched data
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                try:
                    context = await browser.new_context(
                        user_agent=self.user_agent,
                        viewport={'width': 1920, 'height': 1080}
                    )
                    page = await context.new_page()
                    
                    # Set timeout for page operations
                    page.set_default_timeout(30000)
                    
                    # Navigate to the URL
                    response = await page.goto(url, wait_until="domcontentloaded")
                    
                    if response:
                        status_code = response.status
                        headers = response.headers
                        content_type = headers.get('content-type', 'text/html')
                    else:
                        status_code = 200
                        content_type = 'text/html'
                    
                    # Wait for network to be idle (with timeout)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except PlaywrightTimeoutError:
                        logger.debug(f"Network idle timeout for {url}, continuing...")
                    
                    # Extract page content and metadata
                    content = await page.content()
                    title = await page.title()
                    
                    return CrawlResult(
                        status_code=status_code,
                        content_type=content_type,
                        content=content,
                        title=title
                    )
                    
                finally:
                    await browser.close()
                    
        except PlaywrightError as e:
            logger.error(f"Playwright error crawling {url}: {e}")
            return CrawlResult(
                status_code=500,
                content_type=None,
                content="",
                title=None,
                error=f"Playwright error: {str(e)[:500]}"
            )
        except Exception as e:
            logger.error(f"Unexpected error with Playwright for {url}: {e}")
            return CrawlResult(
                status_code=500,
                content_type=None,
                content="",
                title=None,
                error=f"Unexpected error: {str(e)[:500]}"
            )
    
    async def fetch_with_httpx(self, url: str) -> CrawlResult:
        """
        Fetch a URL using httpx for non-JavaScript content.
        
        Args:
            url: The URL to fetch
            
        Returns:
            CrawlResult with the fetched data
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": self.user_agent},
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            ) as client:
                response = await client.get(url)
                
                status_code = response.status_code
                content_type = response.headers.get('content-type', '')
                content = response.text
                
                return CrawlResult(
                    status_code=status_code,
                    content_type=content_type,
                    content=content,
                    title=None  # Will be extracted by HTML parser
                )
                
        except httpx.RequestError as e:
            logger.error(f"HTTP request error crawling {url}: {e}")
            return CrawlResult(
                status_code=0,
                content_type=None,
                content="",
                title=None,
                error=f"Request error: {str(e)[:500]}"
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP status error crawling {url}: {e.response.status_code}")
            return CrawlResult(
                status_code=e.response.status_code,
                content_type=e.response.headers.get('content-type'),
                content="",
                title=None,
                error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return CrawlResult(
                status_code=500,
                content_type=None,
                content="",
                title=None,
                error=f"Unexpected error: {str(e)[:500]}"
            )
    
    async def fetch(self, url: str, use_javascript: bool = False) -> CrawlResult:
        """
        Fetch a URL using the appropriate method.
        
        Args:
            url: The URL to fetch
            use_javascript: Whether to use Playwright for JavaScript rendering
            
        Returns:
            CrawlResult with the fetched data
        """
        if use_javascript:
            return await self.fetch_with_playwright(url)
        else:
            return await self.fetch_with_httpx(url)