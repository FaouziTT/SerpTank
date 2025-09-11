"""
URL utilities for the crawler service.

This module provides URL normalization, domain extraction,
and URL filtering functionality.
"""
import re
from typing import Set
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent storage and comparison.
    
    Args:
        url: The URL to normalize
        
    Returns:
        The normalized URL
    """
    try:
        parsed = urlparse(url.strip())
        
        # Normalize scheme and netloc to lowercase
        scheme = parsed.scheme.lower() if parsed.scheme else 'https'
        netloc = parsed.netloc.lower() if parsed.netloc else ''
        
        # Remove default ports
        if ':80' in netloc and scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        # Remove fragment identifier
        fragment = ''
        
        # Reconstruct URL
        normalized = urlunparse((
            scheme,
            netloc,
            parsed.path or '/',
            parsed.params,
            parsed.query,
            fragment
        ))
        
        return normalized
        
    except Exception:
        return url.strip()


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def should_crawl_url(
    source_url: str,
    target_url: str,
    urls_crawled_set: Set[str],
    urls_to_crawl: Set[str],
    follow_external_links: bool
) -> bool:
    """
    Determine if a URL should be crawled.
    
    Args:
        source_url: The URL that contains the link
        target_url: The URL to check
        urls_crawled_set: Set of already crawled URLs
        urls_to_crawl: Set of URLs in the queue
        follow_external_links: Whether to follow external links
        
    Returns:
        True if the URL should be crawled, False otherwise
    """
    # Skip non-HTTP URLs
    if not target_url.startswith(('http://', 'https://')):
        return False
    
    # Normalize target URL
    normalized_target = normalize_url(target_url)
    
    # Skip URLs that have already been crawled or are in the queue
    if (normalized_target in urls_crawled_set or 
        normalized_target in urls_to_crawl):
        return False
    
    # Check if we should follow external links
    if not follow_external_links:
        source_domain = extract_domain(source_url)
        target_domain = extract_domain(target_url)
        
        if source_domain != target_domain:
            return False
    
    # Skip common file extensions that are not web pages
    skip_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                      '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png', 
                      '.gif', '.bmp', '.svg', '.ico', '.css', '.js', '.json', 
                      '.xml', '.rss', '.atom', '.mp3', '.mp4', '.avi', '.mov'}
    
    parsed_url = urlparse(normalized_target)
    path_lower = parsed_url.path.lower()
    
    for ext in skip_extensions:
        if path_lower.endswith(ext):
            return False
    
    return True