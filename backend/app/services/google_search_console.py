"""
Google Search Console Service for Real Search Performance Data

This service provides functionality to interact with Google Search Console API
for search performance, indexing status, and technical SEO data.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import os
import random
import re
from urllib.parse import urlparse, urlunparse

try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as UserCredentials
    from google.auth.exceptions import GoogleAuthError
    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleSearchConsoleClient:
    """Client for Google Search Console API with OAuth and Service Account support."""
    
    def __init__(self, access_token: Optional[str] = None, site_url: Optional[str] = None):
        """
        Initialize GSC client.
        
        Args:
            access_token: OAuth access token for user-owned data
            site_url: Specific site URL to analyze
        """
        self.access_token = access_token
        self.site_url = site_url or settings.DEFAULT_SITE_URL
        self.property_url = self._normalize_property_url(site_url or settings.DEFAULT_SITE_PROPERTY)
        self.service = None
        self._initialize_service()
    
    def _normalize_property_url(self, url: Optional[str]) -> Optional[str]:
        """
        Normalize a URL for Google Search Console property format.
        
        Args:
            url: Raw URL input
            
        Returns:
            Properly formatted URL for GSC API calls
        """
        if not url:
            return None
            
        url = url.strip()
        if not url:
            return None
            
        # Fix common URL issues
        # Replace dashes with dots in domain names (serptank-com -> serptank.com)
        if 'serptank-com' in url:
            url = url.replace('serptank-com', 'serptank.com')
            logger.info(f"Fixed malformed domain in URL: {url}")
            
        # Parse the URL to extract components
        try:
            parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
            domain = parsed.netloc or parsed.path
            
            # Clean up domain
            if domain:
                # Remove trailing slashes and clean up
                domain = domain.rstrip('/')
                
                # Return clean domain for Domain Property format
                # GSC prefers domain properties without protocol for most cases
                return domain
            else:
                logger.warning(f"Could not parse domain from URL: {url}")
                return url
                
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return url
    
    def _get_possible_property_urls(self, base_url: str) -> List[str]:
        """
        Get all possible property URL formats that might be registered in GSC.
        
        Args:
            base_url: Base URL to generate variations from
            
        Returns:
            List of possible property URL formats
        """
        if not base_url:
            return []
            
        base_url = base_url.strip()
        
        # First normalize the URL to fix common issues
        normalized_url = self._normalize_property_url(base_url)
        if not normalized_url:
            return []
            
        variations = []
        
        try:
            # Use normalized URL for generating variations
            if not normalized_url.startswith(('http://', 'https://')):
                full_url = f'https://{normalized_url}'
            else:
                full_url = normalized_url
                
            parsed = urlparse(full_url)
            domain = parsed.netloc
            
            # CRITICAL: Add Domain Property format first (most common for new properties)
            # Domain properties use sc-domain: prefix
            if domain:
                variations.append(f'sc-domain:{domain}')
                logger.info(f"Added domain property format: sc-domain:{domain}")
            
            if domain:
                # Domain Property format (preferred for most cases)
                variations.append(domain)
                
                # URL-prefix property formats
                variations.append(f'https://{domain}/')
                variations.append(f'http://{domain}/')
                variations.append(f'https://{domain}')
                variations.append(f'http://{domain}')
                
                # Also try with www. prefix if not already present
                if not domain.startswith('www.'):
                    www_domain = f'www.{domain}'
                    variations.extend([
                        www_domain,
                        f'https://{www_domain}/',
                        f'http://{www_domain}/',
                        f'https://{www_domain}',
                        f'http://{www_domain}'
                    ])
                
                # Remove duplicates while preserving order
                seen = set()
                unique_variations = []
                for var in variations:
                    if var not in seen:
                        seen.add(var)
                        unique_variations.append(var)
                        
                return unique_variations
                
        except Exception as e:
            logger.warning(f"Error generating URL variations for {base_url}: {e}")
            
        return [base_url]  # Fallback to original
    
    def _initialize_service(self):
        """Initialize the GSC service with OAuth or Service Account credentials."""
        if not GSC_AVAILABLE:
            logger.warning("Google Search Console API not available. Install google-api-python-client package.")
            return
        
        try:
            credentials = None
            
            if self.access_token:
                # Use OAuth access token for user-owned data
                credentials = UserCredentials(
                    token=self.access_token,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                logger.info("Using OAuth authentication for GSC")
                
            elif settings.GOOGLE_APPLICATION_CREDENTIALS:
                # Use service account authentication for public analysis
                credentials = ServiceAccountCredentials.from_service_account_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                logger.info(f"Using service account authentication for GSC: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
            else:
                logger.warning("No Google credentials configured for GSC")
                return
            
            # Build the Search Console service
            self.service = build('searchconsole', 'v1', credentials=credentials)
            logger.info("GSC service initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize GSC service: {e}")
            self.service = None
    
    def is_configured(self) -> bool:
        """Check if GSC is properly configured."""
        return bool(
            self.site_url and 
            self.site_url.strip() and
            self.property_url and 
            self.property_url.strip()
        )
    
    def is_authenticated(self) -> bool:
        """Check if GSC authentication is working."""
        if not GSC_AVAILABLE:
            return False
        
        if not self.is_configured():
            return False
            
        return self.service is not None
    
    async def _find_best_property_url(self) -> Optional[str]:
        """
        Find the best property URL by checking what's actually available in the user's GSC account.
        
        Returns:
            The best matching property URL, or None if nothing matches
        """
        if not self.access_token or not self.service:
            logger.warning("OAuth token required to query user sites")
            return self.property_url
            
        try:
            # Get user's available sites
            user_sites = await self.get_user_sites()
            
            if not user_sites:
                logger.warning("No sites found in user's GSC account")
                return self.property_url
                
            site_urls = [site['site_url'] for site in user_sites]
            logger.info(f"Available sites in GSC: {site_urls}")
            
            # If property_url is not set, can't match
            if not self.property_url:
                logger.warning("No property URL to match against")
                return site_urls[0] if site_urls else None
                
            # Generate possible variations of our target URL
            possible_urls = self._get_possible_property_urls(self.property_url)
            
            # Find the first match
            for url in possible_urls:
                if url in site_urls:
                    logger.info(f"Found matching site in GSC: {url}")
                    return url
                    
            # If no exact match, try partial matches (for different protocols)
            base_domain = self.property_url
            if '://' in base_domain:
                base_domain = urlparse(base_domain).netloc
                
            for site_url in site_urls:
                site_domain = site_url
                if '://' in site_domain:
                    site_domain = urlparse(site_domain).netloc
                    
                if base_domain == site_domain:
                    logger.info(f"Found domain match in GSC: {site_url} (matches {base_domain})")
                    return site_url
                    
            logger.warning(f"No matching site found in GSC for {self.property_url}. Available: {site_urls}")
            return self.property_url  # Fallback to original
            
        except Exception as e:
            logger.error(f"Error finding best property URL: {e}")
            return self.property_url
    
    async def get_user_sites(self) -> List[Dict[str, Any]]:
        """
        Get list of sites that the user has access to in Search Console.
        Only works with OAuth authentication.
        
        Returns:
            List of site information dictionaries
        """
        if not self.is_authenticated():
            return []
        
        if not self.access_token:
            logger.warning("get_user_sites requires OAuth authentication")
            return []
        
        try:
            sites_list = self.service.sites().list().execute()
            sites = sites_list.get('siteEntry', [])
            
            result = []
            for site in sites:
                site_info = {
                    'site_url': site.get('siteUrl'),
                    'permission_level': site.get('permissionLevel'),
                    'verified': True  # If it's in the list, it's verified
                }
                result.append(site_info)
            
            logger.info(f"Found {len(result)} sites for user: {[s['site_url'] for s in result]}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching user sites from GSC: {e}")
            return []
    
    def _try_gsc_request_with_url_variations(self, request_func, *args, **kwargs) -> Any:
        """
        Try a GSC API request with different URL variations until one succeeds.
        
        Args:
            request_func: Function to call for the API request
            *args: Arguments to pass to the request function
            **kwargs: Keyword arguments to pass to the request function
            
        Returns:
            API response
            
        Raises:
            Exception: If all URL variations fail
        """
        if not self.property_url:
            raise ValueError("No property URL configured")
            
        possible_urls = self._get_possible_property_urls(self.property_url)
        last_error = None
        
        for url in possible_urls:
            try:
                logger.info(f"Trying GSC request with property URL: {url}")
                return request_func(url, *args, **kwargs)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # If it's a "not a valid site URL" error, try next variation
                if 'not a valid' in error_msg and 'site url' in error_msg:
                    logger.warning(f"Property URL {url} not found in user's GSC account, trying next variation")
                    last_error = e
                    continue
                    
                # If it's a 404 or similar access error, try next variation  
                elif 'notfound' in error_msg or '404' in error_msg or 'forbidden' in error_msg:
                    logger.warning(f"Access denied for property URL {url}, trying next variation")
                    last_error = e
                    continue
                    
                # For other errors, re-raise immediately
                else:
                    logger.error(f"Non-URL related error with {url}: {e}")
                    raise
                    
        # If we get here, all variations failed
        error_msg = f"All property URL variations failed. Last error: {last_error}"
        logger.error(error_msg)
        logger.error(f"Tried these URLs: {possible_urls}")
        raise ValueError(error_msg)
    
    async def get_search_performance(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        dimensions: Optional[List[str]] = None,
        search_type: str = "web"
    ) -> Dict[str, Any]:
        """
        Get search performance data from GSC.
        
        Args:
            start_date: Start date (YYYY-MM-DD format or relative like "30daysAgo")
            end_date: End date (YYYY-MM-DD format or relative like "today")
            dimensions: List of dimensions (query, page, country, device, etc.)
            search_type: Type of search (web, image, video)
            
        Returns:
            Search performance data including clicks, impressions, CTR, position
            
        Raises:
            ValueError: If GSC is not configured or authenticated
            Exception: If API request fails
        """
        if not self.is_authenticated():
            raise ValueError("Google Search Console is not authenticated. Please configure OAuth or service account credentials.")
        
        try:
            # For OAuth users, try to find the best matching property URL
            if self.access_token:
                best_url = await self._find_best_property_url()
                if best_url and best_url != self.property_url:
                    logger.info(f"Using auto-detected property URL: {best_url} (instead of {self.property_url})")
                    self.property_url = best_url
                    
            # Convert relative dates to actual dates
            if start_date == "30daysAgo":
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            elif start_date == "7daysAgo":
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            if end_date == "today":
                end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")  # GSC data is 1 day behind
            
            # Set default dimensions if none provided
            if not dimensions:
                dimensions = ['date']
            
            # Build the request
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'searchType': search_type,
                'rowLimit': 1000
            }
            
            # Execute the search analytics query with URL variations
            def make_request(site_url: str) -> dict:
                return self.service.searchanalytics().query(
                    siteUrl=site_url,
                    body=request
                ).execute()
                
            response = self._try_gsc_request_with_url_variations(make_request)
            
            # Process the response
            performance_data = {
                "total_clicks": 0,
                "total_impressions": 0,
                "average_ctr": 0,
                "average_position": 0,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "daily_breakdown": [],
                "top_queries": [],
                "top_pages": []
            }
            
            if 'rows' in response:
                rows = response['rows']
                
                # Calculate totals
                total_clicks = sum(row.get('clicks', 0) for row in rows)
                total_impressions = sum(row.get('impressions', 0) for row in rows)
                
                performance_data.update({
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "average_ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                    "average_position": sum(row.get('position', 0) for row in rows) / len(rows) if rows else 0
                })
                
                # Process daily breakdown if date dimension is present
                if 'date' in dimensions:
                    daily_data = {}
                    for row in rows:
                        date = row.get('keys', [''])[0]
                        if date not in daily_data:
                            daily_data[date] = {
                                'clicks': 0,
                                'impressions': 0,
                                'ctr': 0,
                                'position': 0
                            }
                        
                        daily_data[date]['clicks'] += row.get('clicks', 0)
                        daily_data[date]['impressions'] += row.get('impressions', 0)
                        daily_data[date]['position'] += row.get('position', 0)
                    
                    # Convert to list and calculate CTR
                    for date, data in daily_data.items():
                        data['ctr'] = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
                        data['position'] = data['position'] / len([r for r in rows if r.get('keys', [''])[0] == date]) if any(r.get('keys', [''])[0] == date for r in rows) else 0
                        performance_data['daily_breakdown'].append({
                            'date': date,
                            **data
                        })
                    
                    # Sort by date
                    performance_data['daily_breakdown'].sort(key=lambda x: x['date'])
                
                # Process top queries if query dimension is present
                if 'query' in dimensions:
                    query_data = {}
                    for row in rows:
                        query = row.get('keys', [''])[0]
                        if query not in query_data:
                            query_data[query] = {
                                'clicks': 0,
                                'impressions': 0,
                                'ctr': 0,
                                'position': 0
                            }
                        
                        query_data[query]['clicks'] += row.get('clicks', 0)
                        query_data[query]['impressions'] += row.get('impressions', 0)
                        query_data[query]['position'] += row.get('position', 0)
                    
                    # Calculate CTR and convert to list
                    for query, data in query_data.items():
                        data['ctr'] = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
                        data['position'] = data['position'] / len([r for r in rows if r.get('keys', [''])[0] == query]) if any(r.get('keys', [''])[0] == query for r in rows) else 0
                        performance_data['top_queries'].append({
                            'query': query,
                            **data
                        })
                    
                    # Sort by clicks descending
                    performance_data['top_queries'].sort(key=lambda x: x['clicks'], reverse=True)
                    performance_data['top_queries'] = performance_data['top_queries'][:50]  # Top 50 queries
                
                # Process top pages if page dimension is present
                if 'page' in dimensions:
                    page_data = {}
                    for row in rows:
                        page = row.get('keys', [''])[0]
                        if page not in page_data:
                            page_data[page] = {
                                'clicks': 0,
                                'impressions': 0,
                                'ctr': 0,
                                'position': 0
                            }
                        
                        page_data[page]['clicks'] += row.get('clicks', 0)
                        page_data[page]['impressions'] += row.get('impressions', 0)
                        page_data[page]['position'] += row.get('position', 0)
                    
                    # Calculate CTR and convert to list
                    for page, data in page_data.items():
                        data['ctr'] = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
                        data['position'] = data['position'] / len([r for r in rows if r.get('keys', [''])[0] == page]) if any(r.get('keys', [''])[0] == page for r in rows) else 0
                        performance_data['top_pages'].append({
                            'page': page,
                            **data
                        })
                    
                    # Sort by clicks descending
                    performance_data['top_pages'].sort(key=lambda x: x['clicks'], reverse=True)
                    performance_data['top_pages'] = performance_data['top_pages'][:50]  # Top 50 pages
            
            return performance_data
            
        except Exception as e:
            logger.error(f"GSC search performance error: {e}")
            raise ValueError(f"Failed to fetch search performance from Google Search Console: {e}")
    
    async def get_top_queries(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get top performing queries from GSC.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Maximum number of queries to return
            
        Returns:
            Top performing queries with performance metrics
            
        Raises:
            ValueError: If GSC is not configured or authenticated
            Exception: If API request fails
        """
        if not self.is_authenticated():
            raise ValueError("Google Search Console is not authenticated. Please configure OAuth or service account credentials.")
        
        try:
            # Get search performance with query dimension
            performance_data = await self.get_search_performance(
                start_date=start_date,
                end_date=end_date,
                dimensions=['query']
            )
            
            # Return top queries up to the limit
            top_queries = performance_data.get('top_queries', [])[:limit]
            
            return {
                "queries": top_queries,
                "total_queries": len(top_queries),
                "date_range": performance_data.get('date_range', {}),
                "total_clicks": performance_data.get('total_clicks', 0),
                "total_impressions": performance_data.get('total_impressions', 0)
            }
            
        except Exception as e:
            logger.error(f"GSC top queries error: {e}")
            raise ValueError(f"Failed to fetch top queries from Google Search Console: {e}")
    
    async def get_top_pages(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get top performing pages from GSC.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Maximum number of pages to return
            
        Returns:
            Top performing pages with performance metrics
            
        Raises:
            ValueError: If GSC is not configured or authenticated
            Exception: If API request fails
        """
        if not self.is_authenticated():
            raise ValueError("Google Search Console is not authenticated. Please configure OAuth or service account credentials.")
        
        try:
            # Get search performance with page dimension
            performance_data = await self.get_search_performance(
                start_date=start_date,
                end_date=end_date,
                dimensions=['page']
            )
            
            # Return top pages up to the limit
            top_pages = performance_data.get('top_pages', [])[:limit]
            
            return {
                "pages": top_pages,
                "total_pages": len(top_pages),
                "date_range": performance_data.get('date_range', {}),
                "total_clicks": performance_data.get('total_clicks', 0),
                "total_impressions": performance_data.get('total_impressions', 0)
            }
            
        except Exception as e:
            logger.error(f"GSC top pages error: {e}")
            raise ValueError(f"Failed to fetch top pages from Google Search Console: {e}")


# Create a singleton instance for public analysis
gsc_client = GoogleSearchConsoleClient()

# Export alias for compatibility
search_console_client = gsc_client

def get_gsc_client(access_token: Optional[str] = None, site_url: Optional[str] = None) -> GoogleSearchConsoleClient:
    """
    Get a GSC client configured for the specific user/site.
    
    Args:
        access_token: OAuth access token for user-owned data
        site_url: Specific site URL to analyze
        
    Returns:
        Configured GSC client
    """
    if access_token or site_url:
        return GoogleSearchConsoleClient(access_token=access_token, site_url=site_url)
    else:
        return gsc_client
