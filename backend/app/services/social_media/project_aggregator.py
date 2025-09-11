"""
Project-specific Social Media Aggregator.

This module aggregates data from multiple social media platforms
using project-specific API credentials.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.social_media_credential import SocialMediaCredential
from .twitter import TwitterService
from .facebook import FacebookService
from .linkedin import LinkedInService

logger = logging.getLogger(__name__)


class ProjectSocialMediaAggregator:
    """Aggregates social media data using project-specific credentials."""
    
    def __init__(self, project_id: int, db: AsyncSession):
        self.project_id = project_id
        self.db = db
        self._services: Dict[str, Any] = {}
        self._credentials_loaded = False
    
    async def _load_credentials(self):
        """Load project-specific social media credentials."""
        if self._credentials_loaded:
            return
        
        result = await self.db.execute(
            select(SocialMediaCredential).where(
                SocialMediaCredential.project_id == self.project_id,
                SocialMediaCredential.is_connected == True
            )
        )
        credentials = result.scalars().all()
        
        for cred in credentials:
            try:
                if cred.platform == "twitter" and cred.api_key and cred.access_token:
                    self._services["twitter"] = TwitterService(
                        api_key=cred.api_key,
                        api_secret=cred.api_secret,
                        access_token=cred.access_token,
                        access_token_secret=cred.access_token_secret
                    )
                    logger.info(f"Loaded Twitter credentials for project {self.project_id}")
                    
                elif cred.platform == "facebook" and cred.access_token:
                    self._services["facebook"] = FacebookService(
                        access_token=cred.access_token,
                        page_id=cred.account_id
                    )
                    logger.info(f"Loaded Facebook credentials for project {self.project_id}")
                    
                elif cred.platform == "linkedin" and cred.access_token:
                    self._services["linkedin"] = LinkedInService(
                        access_token=cred.access_token,
                        company_id=cred.account_id
                    )
                    logger.info(f"Loaded LinkedIn credentials for project {self.project_id}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize {cred.platform} service: {str(e)}")
        
        self._credentials_loaded = True
    
    async def get_brand_mentions(
        self,
        brand_name: str,
        include_hashtags: bool = True
    ) -> Dict[str, Any]:
        """Get brand mentions across configured platforms."""
        await self._load_credentials()
        
        results = {
            'brand_name': brand_name,
            'project_id': self.project_id,
            'platforms': {},
            'summary': {
                'total_mentions': 0,
                'total_engagement': 0,
                'platforms_active': len(self._services),
                'sentiment_breakdown': {
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                }
            },
            'fetched_at': datetime.utcnow().isoformat()
        }
        
        # Fetch data from each configured platform
        tasks = []
        
        if 'twitter' in self._services:
            tasks.append(self._fetch_twitter_mentions(brand_name, include_hashtags))
        
        if 'facebook' in self._services:
            tasks.append(self._fetch_facebook_data())
        
        if 'linkedin' in self._services:
            tasks.append(self._fetch_linkedin_data())
        
        if tasks:
            platform_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            platform_names = list(self._services.keys())
            for i, result in enumerate(platform_results):
                platform = platform_names[i]
                if isinstance(result, Exception):
                    results['platforms'][platform] = {
                        'error': str(result),
                        'status': 'failed'
                    }
                else:
                    results['platforms'][platform] = result
                    
                    # Update summary
                    if 'mentions' in result:
                        results['summary']['total_mentions'] += result['mentions']
                    if 'engagement' in result:
                        results['summary']['total_engagement'] += result['engagement']
        else:
            results['summary']['message'] = "No social media platforms configured for this project"
        
        return results
    
    async def _fetch_twitter_mentions(self, brand_name: str, include_hashtags: bool) -> Dict[str, Any]:
        """Fetch Twitter mentions."""
        service = self._services['twitter']
        result = {
            'platform': 'twitter',
            'mentions': 0,
            'engagement': 0,
            'recent_posts': [],
            'top_posts': []
        }
        
        try:
            # Search for brand mentions
            mentions_data = await service.search_mentions(brand_name)
            if mentions_data and 'mentions' in mentions_data:
                result['mentions'] = len(mentions_data['mentions'])
                result['recent_posts'] = mentions_data['mentions'][:5]
                
                # Calculate engagement
                for mention in mentions_data['mentions']:
                    metrics = mention.get('metrics', {})
                    result['engagement'] += (
                        metrics.get('like_count', 0) +
                        metrics.get('retweet_count', 0) +
                        metrics.get('reply_count', 0)
                    )
            
            # Search hashtags if requested
            if include_hashtags:
                hashtag_data = await service.get_hashtag_analytics(brand_name)
                if hashtag_data:
                    result['hashtag_analytics'] = hashtag_data
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _fetch_facebook_data(self) -> Dict[str, Any]:
        """Fetch Facebook data."""
        service = self._services['facebook']
        result = {
            'platform': 'facebook',
            'page_metrics': {},
            'recent_posts': [],
            'audience': {}
        }
        
        try:
            # Get page insights
            insights = await service.get_page_insights()
            if insights:
                result['page_metrics'] = insights.get('insights', {})
            
            # Get recent posts
            posts = await service.get_recent_posts(limit=5)
            if posts:
                result['recent_posts'] = posts.get('posts', [])
                
                # Calculate total engagement
                engagement = 0
                for post in posts.get('posts', []):
                    engagement += post.get('engagement', {}).get('total', 0)
                result['engagement'] = engagement
            
            # Get audience demographics
            demographics = await service.get_audience_demographics()
            if demographics:
                result['audience'] = demographics
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _fetch_linkedin_data(self) -> Dict[str, Any]:
        """Fetch LinkedIn data."""
        service = self._services['linkedin']
        result = {
            'platform': 'linkedin',
            'company_metrics': {},
            'recent_updates': [],
            'follower_statistics': {}
        }
        
        try:
            # Get company statistics
            stats = await service.get_company_statistics()
            if stats:
                result['company_metrics'] = stats.get('statistics', {})
                result['mentions'] = stats.get('mention_count', 0)
            
            # Get recent updates
            updates = await service.get_company_updates(count=5)
            if updates:
                result['recent_updates'] = updates.get('updates', [])
                
                # Calculate engagement
                engagement = 0
                for update in updates.get('updates', []):
                    engagement += (
                        update.get('likes', 0) +
                        update.get('comments', 0) +
                        update.get('shares', 0)
                    )
                result['engagement'] = engagement
            
            # Get follower statistics
            followers = await service.get_follower_statistics()
            if followers:
                result['follower_statistics'] = followers
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def get_social_signals(self, url: str) -> Dict[str, Any]:
        """Get social signals for a specific URL."""
        await self._load_credentials()
        
        results = {
            'url': url,
            'project_id': self.project_id,
            'signals': {},
            'total_shares': 0,
            'total_engagement': 0,
            'fetched_at': datetime.utcnow().isoformat()
        }
        
        # Twitter URL mentions
        if 'twitter' in self._services:
            try:
                service = self._services['twitter']
                mentions = await service.search_mentions(url)
                
                if mentions and 'mentions' in mentions:
                    engagement = sum(
                        mention.get('metrics', {}).get('like_count', 0) +
                        mention.get('metrics', {}).get('retweet_count', 0)
                        for mention in mentions['mentions']
                    )
                    
                    results['signals']['twitter'] = {
                        'mentions': len(mentions['mentions']),
                        'engagement': engagement
                    }
                    results['total_shares'] += len(mentions['mentions'])
                    results['total_engagement'] += engagement
                    
            except Exception as e:
                results['signals']['twitter'] = {'error': str(e)}
        
        # Facebook URL shares (limited without specific permissions)
        if 'facebook' in self._services:
            results['signals']['facebook'] = {
                'status': 'limited',
                'message': 'URL share data requires additional Graph API permissions'
            }
        
        # LinkedIn URL shares
        if 'linkedin' in self._services:
            results['signals']['linkedin'] = {
                'status': 'limited',
                'message': 'URL share data requires elevated API access'
            }
        
        return results
    
    async def get_platform_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics for all configured platforms."""
        await self._load_credentials()
        
        analytics = {
            'project_id': self.project_id,
            'platforms': {},
            'summary': {
                'total_followers': 0,
                'total_engagement_rate': 0,
                'growth_rate': 0,
                'platforms_configured': len(self._services)
            },
            'fetched_at': datetime.utcnow().isoformat()
        }
        
        # Fetch analytics for each platform
        for platform, service in self._services.items():
            try:
                if platform == 'twitter':
                    # Twitter analytics would require account metrics API access
                    analytics['platforms']['twitter'] = {
                        'status': 'limited',
                        'message': 'Account analytics requires elevated API access'
                    }
                    
                elif platform == 'facebook':
                    insights = await service.get_page_insights()
                    if insights and 'insights' in insights:
                        metrics = insights['insights']
                        analytics['platforms']['facebook'] = {
                            'followers': metrics.get('page_fans', {}).get('value', 0),
                            'engagement_rate': metrics.get('page_engaged_users', {}).get('value', 0),
                            'impressions': metrics.get('page_impressions', {}).get('value', 0),
                            'reach': metrics.get('page_posts_impressions', {}).get('value', 0)
                        }
                        analytics['summary']['total_followers'] += metrics.get('page_fans', {}).get('value', 0)
                        
                elif platform == 'linkedin':
                    stats = await service.get_company_statistics()
                    if stats and 'statistics' in stats:
                        analytics['platforms']['linkedin'] = {
                            'followers': stats['statistics'].get('followerCount', 0),
                            'engagement_rate': stats['statistics'].get('engagementRate', 0)
                        }
                        analytics['summary']['total_followers'] += stats['statistics'].get('followerCount', 0)
                        
            except Exception as e:
                analytics['platforms'][platform] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        return analytics
    
    def get_configured_platforms(self) -> List[str]:
        """Get list of configured platforms for this project."""
        return list(self._services.keys())