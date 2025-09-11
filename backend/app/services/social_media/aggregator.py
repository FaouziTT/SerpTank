"""
Social Media Aggregator.

This module aggregates data from multiple social media platforms
to provide unified social signals and brand monitoring.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from .twitter import TwitterClient
from .facebook import FacebookClient
from .linkedin import LinkedInClient

logger = logging.getLogger(__name__)


class SocialMediaAggregator:
    """Aggregates data from multiple social media platforms."""
    
    def __init__(self):
        self.twitter = TwitterClient()
        self.facebook = FacebookClient()
        self.linkedin = LinkedInClient()
    
    async def get_brand_mentions(
        self,
        brand_name: str,
        include_hashtags: bool = True
    ) -> Dict[str, Any]:
        """
        Get brand mentions across all platforms.
        
        Args:
            brand_name: Brand name to search for
            include_hashtags: Whether to include hashtag variations
            
        Returns:
            Aggregated brand mentions data
        """
        results = {
            'brand_name': brand_name,
            'platforms': {},
            'summary': {
                'total_mentions': 0,
                'total_engagement': 0,
                'sentiment_analysis': 'neutral'  # Placeholder
            },
            'fetched_at': datetime.now().isoformat()
        }
        
        # Search on Twitter
        twitter_results = await self.twitter.search_mentions(brand_name)
        results['platforms']['twitter'] = twitter_results
        if 'mentions' in twitter_results:
            results['summary']['total_mentions'] += len(twitter_results['mentions'])
        
        # Search hashtags if requested
        if include_hashtags:
            hashtag_results = await self.twitter.get_hashtag_analytics(brand_name)
            results['platforms']['twitter_hashtag'] = hashtag_results
        
        # Facebook page insights (if configured)
        facebook_results = await self.facebook.get_page_insights()
        results['platforms']['facebook'] = facebook_results
        
        return results
    
    async def get_social_signals(
        self,
        url: str
    ) -> Dict[str, Any]:
        """
        Get social signals for a specific URL.
        
        Args:
            url: URL to check social signals for
            
        Returns:
            Social signals data across platforms
        """
        results = {
            'url': url,
            'signals': {},
            'total_shares': 0,
            'fetched_at': datetime.now().isoformat()
        }
        
        # Get Twitter mentions of the URL
        twitter_results = await self.twitter.search_mentions(url)
        if 'mentions' in twitter_results:
            results['signals']['twitter'] = {
                'mentions': len(twitter_results['mentions']),
                'engagement': sum(
                    mention.get('metrics', {}).get('like_count', 0) +
                    mention.get('metrics', {}).get('retweet_count', 0)
                    for mention in twitter_results['mentions']
                )
            }
            results['total_shares'] += results['signals']['twitter']['mentions']
        
        # Note: Facebook and LinkedIn have limited URL share data access
        results['signals']['facebook'] = {
            'message': 'Facebook URL share data requires Graph API access'
        }
        results['signals']['linkedin'] = {
            'message': 'LinkedIn URL share data requires elevated permissions'
        }
        
        return results
    
    async def get_competitor_comparison(
        self,
        brand_name: str,
        competitor_names: List[str]
    ) -> Dict[str, Any]:
        """
        Compare brand with competitors across social platforms.
        
        Args:
            brand_name: Your brand name
            competitor_names: List of competitor names
            
        Returns:
            Competitive comparison data
        """
        results = {
            'brand': brand_name,
            'competitors': {},
            'comparison': {},
            'fetched_at': datetime.now().isoformat()
        }
        
        # Get brand mentions
        brand_mentions = await self.get_brand_mentions(brand_name)
        results['brand_data'] = brand_mentions
        
        # Get competitor mentions
        for competitor in competitor_names[:5]:  # Limit to 5 competitors
            competitor_mentions = await self.get_brand_mentions(competitor)
            results['competitors'][competitor] = competitor_mentions
        
        # Calculate comparison metrics
        brand_total = brand_mentions['summary']['total_mentions']
        results['comparison'] = {
            'brand_share_of_voice': 0,
            'ranking': 1,
            'competitors_analysis': []
        }
        
        total_mentions = brand_total
        for comp_name, comp_data in results['competitors'].items():
            comp_mentions = comp_data['summary']['total_mentions']
            total_mentions += comp_mentions
            
            results['comparison']['competitors_analysis'].append({
                'name': comp_name,
                'mentions': comp_mentions,
                'vs_brand': comp_mentions - brand_total
            })
        
        if total_mentions > 0:
            results['comparison']['brand_share_of_voice'] = round(
                (brand_total / total_mentions) * 100, 2
            )
        
        # Sort competitors by mentions
        results['comparison']['competitors_analysis'].sort(
            key=lambda x: x['mentions'], 
            reverse=True
        )
        
        return results
    
    async def get_social_health_score(
        self,
        brand_name: str,
        page_ids: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate overall social media health score.
        
        Args:
            brand_name: Brand name
            page_ids: Dictionary of platform page IDs
            
        Returns:
            Social health score and breakdown
        """
        score_components = {
            'presence': 0,
            'engagement': 0,
            'growth': 0,
            'sentiment': 0,
            'activity': 0
        }
        
        results = {
            'brand_name': brand_name,
            'score': 0,
            'components': score_components,
            'recommendations': [],
            'fetched_at': datetime.now().isoformat()
        }
        
        # Check platform presence
        platform_count = 0
        if self.twitter.client:
            platform_count += 1
        if self.facebook.api:
            platform_count += 1
        if self.linkedin.access_token:
            platform_count += 1
        
        score_components['presence'] = min(100, platform_count * 33)
        
        # Get engagement metrics
        brand_mentions = await self.get_brand_mentions(brand_name)
        if brand_mentions['summary']['total_mentions'] > 0:
            score_components['engagement'] = min(100, brand_mentions['summary']['total_mentions'] * 10)
        
        # Placeholder for other metrics
        score_components['growth'] = 50  # Would need historical data
        score_components['sentiment'] = 70  # Would need sentiment analysis
        score_components['activity'] = 60  # Would need posting frequency data
        
        # Calculate overall score
        results['score'] = sum(score_components.values()) / len(score_components)
        results['components'] = score_components
        
        # Generate recommendations
        if score_components['presence'] < 100:
            results['recommendations'].append(
                "Expand social media presence to more platforms"
            )
        if score_components['engagement'] < 50:
            results['recommendations'].append(
                "Increase engagement through more interactive content"
            )
        if score_components['activity'] < 70:
            results['recommendations'].append(
                "Post more frequently to maintain audience interest"
            )
        
        # Add grade
        if results['score'] >= 90:
            results['grade'] = 'A'
        elif results['score'] >= 80:
            results['grade'] = 'B'
        elif results['score'] >= 70:
            results['grade'] = 'C'
        elif results['score'] >= 60:
            results['grade'] = 'D'
        else:
            results['grade'] = 'F'
        
        return results
    
    async def get_unified_dashboard(
        self,
        brand_name: str,
        include_competitors: bool = False,
        competitor_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get unified social media dashboard data.
        
        Args:
            brand_name: Brand name
            include_competitors: Whether to include competitor data
            competitor_names: List of competitor names
            
        Returns:
            Unified dashboard data
        """
        dashboard = {
            'brand_name': brand_name,
            'overview': {},
            'platforms': {},
            'insights': [],
            'fetched_at': datetime.now().isoformat()
        }
        
        # Get brand mentions
        brand_data = await self.get_brand_mentions(brand_name)
        dashboard['platforms'] = brand_data['platforms']
        
        # Get social health score
        health_score = await self.get_social_health_score(brand_name)
        dashboard['overview']['health_score'] = health_score['score']
        dashboard['overview']['grade'] = health_score['grade']
        
        # Get competitor comparison if requested
        if include_competitors and competitor_names:
            competitor_data = await self.get_competitor_comparison(
                brand_name, 
                competitor_names
            )
            dashboard['competitor_analysis'] = competitor_data['comparison']
        
        # Generate insights
        if health_score['score'] < 70:
            dashboard['insights'].append({
                'type': 'warning',
                'message': 'Social media presence needs improvement',
                'priority': 'high'
            })
        
        if brand_data['summary']['total_mentions'] < 10:
            dashboard['insights'].append({
                'type': 'opportunity',
                'message': 'Low brand visibility - consider social media campaigns',
                'priority': 'medium'
            })
        
        # Add platform-specific metrics
        if 'twitter' in dashboard['platforms'] and not dashboard['platforms']['twitter'].get('error'):
            twitter_mentions = len(dashboard['platforms']['twitter'].get('mentions', []))
            dashboard['overview']['twitter_mentions'] = twitter_mentions
        
        if 'facebook' in dashboard['platforms'] and 'insights' in dashboard['platforms']['facebook']:
            fb_insights = dashboard['platforms']['facebook']['insights']
            if 'page_fans' in fb_insights:
                dashboard['overview']['facebook_fans'] = fb_insights['page_fans'].get('value', 0)
        
        return dashboard


# Create singleton instance for backward compatibility
social_media_aggregator = SocialMediaAggregator()