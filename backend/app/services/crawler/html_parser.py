"""
HTML parsing utilities for the crawler service.

This module provides HTML content parsing, link extraction,
and content analysis functionality.
"""
import re
import logging
from typing import Set, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .url_utils import normalize_url

logger = logging.getLogger(__name__)


def extract_links_from_html(html_content: str, base_url: str) -> Set[str]:
    """
    Extract all links from HTML content.
    
    Args:
        html_content: The HTML content to parse
        base_url: The base URL for resolving relative links
        
    Returns:
        Set of absolute URLs found in the content
    """
    links = set()
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract links from <a> tags
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if href:
                absolute_url = urljoin(base_url, href)
                if absolute_url.startswith(('http://', 'https://')):
                    links.add(normalize_url(absolute_url))
        
        # Extract links from <link> tags (canonical, alternate, etc.)
        for link in soup.find_all('link', href=True):
            href = link.get('href', '').strip()
            if href:
                absolute_url = urljoin(base_url, href)
                if absolute_url.startswith(('http://', 'https://')):
                    links.add(normalize_url(absolute_url))
                    
    except Exception as e:
        logger.warning(f"Failed to parse HTML for links from {base_url}: {e}")
        
        # Fallback to regex if BeautifulSoup fails
        try:
            href_pattern = re.compile(r'href=["\'](.*?)["\']', re.IGNORECASE)
            for match in href_pattern.finditer(html_content):
                href = match.group(1).strip()
                if href:
                    absolute_url = urljoin(base_url, href)
                    if absolute_url.startswith(('http://', 'https://')):
                        links.add(normalize_url(absolute_url))
        except Exception as fallback_error:
            logger.error(f"Fallback link extraction also failed for {base_url}: {fallback_error}")
    
    return links


def extract_title_from_html(html_content: str) -> Optional[str]:
    """
    Extract the title from HTML content.
    
    Args:
        html_content: The HTML content to parse
        
    Returns:
        The page title or None if not found
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()[:500]  # Limit title length
    except Exception:
        # Fallback to regex
        try:
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()[:500]
        except Exception:
            pass
    
    return None


def extract_meta_description(html_content: str) -> Optional[str]:
    """
    Extract meta description from HTML content.
    
    Args:
        html_content: The HTML content to parse
        
    Returns:
        The meta description or None if not found
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Also check for og:description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
            
    except Exception as e:
        logger.debug(f"Failed to extract meta description: {e}")
    
    return None


def extract_headers(html_content: str) -> dict:
    """
    Extract header tags (h1-h6) from HTML content.
    
    Args:
        html_content: The HTML content to parse
        
    Returns:
        Dictionary with header levels as keys and lists of header texts as values
    """
    headers = {f'h{i}': [] for i in range(1, 7)}
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for level in range(1, 7):
            header_tags = soup.find_all(f'h{level}')
            headers[f'h{level}'] = [tag.get_text(strip=True) for tag in header_tags if tag.get_text(strip=True)]
            
    except Exception as e:
        logger.debug(f"Failed to extract headers: {e}")
    
    return headers