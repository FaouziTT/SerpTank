"""
Facebook Graph API Client.

This module provides integration with Facebook Graph API for fetching
page insights, posts analytics, and social signals.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    import facebook
except ImportError:
    facebook = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class FacebookClient:
    """Client for Facebook Graph API."""
    
    def __init__(self):
        self.access_token = getattr(settings, 'FACEBOOK_ACCESS_TOKEN', None)
        self.page_id = getattr(settings, 'FACEBOOK_PAGE_ID', None)
        self.app_id = getattr(settings, 'FACEBOOK_APP_ID', None)
        self.app_secret = getattr(settings, 'FACEBOOK_APP_SECRET', None)
        
        self.api = None
        self.api_version = 'v18.0'  # Latest stable version
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Facebook API client."""
        if not facebook:
            logger.warning("Facebook SDK not installed")
            return
        
        try:
            if self.access_token:
                self.api = facebook.GraphAPI(access_token=self.access_token)
                logger.info("Facebook API client initialized successfully")
            else:
                logger.warning("Facebook Access Token not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Facebook API client: {e}")
    
    async def get_page_insights(self) -> Dict[str, Any]:
        """
        Get Facebook page insights and metrics.
        
        Returns:
            Facebook page insights data
        """
        if not self.api or not self.page_id:
            return {
                'error': 'Facebook API not configured',
                'insights': {}
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_page_insights_sync
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting Facebook page insights: {e}")
            return {
                'error': str(e),
                'insights': {}
            }
    
    def _get_page_insights_sync(self) -> Dict[str, Any]:
        """Synchronous method to get page insights."""
        # Define metrics to fetch
        metrics = [
            'page_impressions',
            'page_engaged_users',
            'page_post_engagements',
            'page_views_total',
            'page_fans',
            'page_fan_adds',
            'page_fan_removes'
        ]
        
        # Fetch insights
        insights_data = self.api.get_object(
            f'/{self.page_id}/insights',
            fields=','.join(metrics),
            period='day',
            since=(datetime.now() - timedelta(days=30)).isoformat()
        )
        
        # Process insights
        insights = {}
        if 'data' in insights_data:
            for metric in insights_data['data']:
                metric_name = metric['name']
                if 'values' in metric and metric['values']:
                    # Get the latest value
                    latest_value = metric['values'][-1]
                    insights[metric_name] = {
                        'value': latest_value['value'],
                        'end_time': latest_value.get('end_time', '')
                    }
        
        # Fetch page info
        page_info = self.api.get_object(
            f'/{self.page_id}',
            fields='name,fan_count,about,category'
        )
        
        return {
            'page_info': page_info,
            'insights': insights,
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_recent_posts(
        self,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get recent posts from Facebook page.
        
        Args:
            limit: Number of posts to fetch
            
        Returns:
            Recent posts with engagement metrics
        """
        if not self.api or not self.page_id:
            return {
                'error': 'Facebook API not configured',
                'posts': []
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_recent_posts_sync,
                limit
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting Facebook posts: {e}")
            return {
                'error': str(e),
                'posts': []
            }
    
    def _get_recent_posts_sync(self, limit: int) -> Dict[str, Any]:
        """Synchronous method to get recent posts."""
        # Fetch posts
        posts_data = self.api.get_object(
            f'/{self.page_id}/posts',
            fields='message,created_time,shares,likes.summary(true),comments.summary(true)',
            limit=min(limit, 100)
        )
        
        posts = []
        if 'data' in posts_data:
            for post in posts_data['data']:
                post_info = {
                    'post_id': post['id'],
                    'message': post.get('message', ''),
                    'created_time': post.get('created_time', ''),
                    'shares': post.get('shares', {}).get('count', 0) if 'shares' in post else 0,
                    'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0)
                }
                
                # Calculate total engagement
                post_info['total_engagement'] = (
                    post_info['likes'] + 
                    post_info['comments'] + 
                    post_info['shares']
                )
                
                posts.append(post_info)
        
        return {
            'posts': posts,
            'total_posts': len(posts),
            'fetched_at': datetime.now().isoformat()
        }
    
    async def search_mentions(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Search for brand mentions on Facebook (limited to public posts).
        
        Args:
            query: Search query
            
        Returns:
            Public mentions data
        """
        # Note: Facebook has limited public search capabilities
        # This is a placeholder for when/if Facebook opens up more search APIs
        logger.warning("Facebook public search is limited by API restrictions")
        
        return {
            'query': query,
            'mentions': [],
            'message': 'Facebook public search is restricted by API limitations',
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_audience_demographics(self) -> Dict[str, Any]:
        """
        Get audience demographics data.
        
        Returns:
            Audience demographics breakdown
        """
        if not self.api or not self.page_id:
            return {
                'error': 'Facebook API not configured',
                'demographics': {}
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_audience_demographics_sync
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting audience demographics: {e}")
            return {
                'error': str(e),
                'demographics': {}
            }
    
    def _get_audience_demographics_sync(self) -> Dict[str, Any]:
        """Synchronous method to get audience demographics."""
        # Fetch audience insights
        insights_data = self.api.get_object(
            f'/{self.page_id}/insights',
            fields='page_fans_gender_age,page_fans_country,page_fans_city',
            period='lifetime'
        )
        
        demographics = {
            'gender_age': {},
            'countries': {},
            'cities': {}
        }
        
        if 'data' in insights_data:
            for metric in insights_data['data']:
                if metric['name'] == 'page_fans_gender_age' and metric['values']:
                    demographics['gender_age'] = metric['values'][0].get('value', {})
                elif metric['name'] == 'page_fans_country' and metric['values']:
                    demographics['countries'] = metric['values'][0].get('value', {})
                elif metric['name'] == 'page_fans_city' and metric['values']:
                    demographics['cities'] = metric['values'][0].get('value', {})
        
        return {
            'demographics': demographics,
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_competitor_analysis(
        self,
        competitor_page_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Get basic competitor analysis (public data only).
        
        Args:
            competitor_page_ids: List of competitor page IDs
            
        Returns:
            Competitor comparison data
        """
        if not self.api:
            return {
                'error': 'Facebook API not configured',
                'competitors': []
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_competitor_analysis_sync,
                competitor_page_ids
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting competitor analysis: {e}")
            return {
                'error': str(e),
                'competitors': []
            }
    
    def _get_competitor_analysis_sync(self, competitor_page_ids: List[str]) -> Dict[str, Any]:
        """Synchronous method to get competitor analysis."""
        competitors = []
        
        for page_id in competitor_page_ids[:5]:  # Limit to 5 competitors
            try:
                # Fetch public page info
                page_info = self.api.get_object(
                    f'/{page_id}',
                    fields='name,fan_count,about,category,engagement'
                )
                
                competitors.append({
                    'page_id': page_id,
                    'name': page_info.get('name', ''),
                    'fan_count': page_info.get('fan_count', 0),
                    'category': page_info.get('category', ''),
                    'engagement': page_info.get('engagement', {})
                })
                
            except Exception as e:
                logger.error(f"Error fetching competitor {page_id}: {e}")
                competitors.append({
                    'page_id': page_id,
                    'error': str(e)
                })
        
        return {
            'competitors': competitors,
            'fetched_at': datetime.now().isoformat()
        }