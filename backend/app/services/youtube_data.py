"""
YouTube Data API Integration.

This module provides integration with YouTube Data API to fetch
video performance data, channel analytics, and SEO insights.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os

from googleapiclient.discovery import build
from google.auth.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeDataClient:
    """Client for YouTube Data API."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'YOUTUBE_DATA_API_KEY', None) or settings.GOOGLE_PAGESPEED_API_KEY
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize YouTube Data API service."""
        try:
            if self.api_key:
                self.service = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube Data API service initialized successfully")
            else:
                logger.warning("YouTube Data API key not configured")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube Data API service: {e}")
    
    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = 'relevance'
    ) -> Dict[str, Any]:
        """
        Search for videos on YouTube.
        
        Args:
            query: Search query
            max_results: Maximum number of results (1-50)
            order: Search order ('relevance', 'date', 'rating', 'viewCount', 'title')
            
        Returns:
            Video search results
        """
        if not self.service:
            raise Exception("YouTube Data API not configured")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._search_videos_sync, 
                query, 
                max_results, 
                order
            )            
            return result
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            raise Exception(f"Failed to search videos: {e}")
    
    def _search_videos_sync(self, query: str, max_results: int, order: str) -> Dict[str, Any]:
        """Synchronous method to search videos."""
        request = self.service.search().list(
            part='snippet',
            q=query,
            type='video',
            order=order,
            maxResults=min(max_results, 50)
        )
        
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # Get detailed video statistics
            video_stats = self._get_video_statistics(video_id)
            
            videos.append({
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet['description'][:500] + '...' if len(snippet['description']) > 500 else snippet['description'],
                'published_at': snippet['publishedAt'],
                'channel_title': snippet['channelTitle'],
                'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'statistics': video_stats
            })
        
        return {
            'query': query,
            'total_results': len(videos),
            'videos': videos,
            'fetched_at': datetime.now().isoformat()
        }
    
    def _get_video_statistics(self, video_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a video."""
        try:
            request = self.service.videos().list(
                part='statistics,contentDetails',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                stats = response['items'][0]['statistics']
                content_details = response['items'][0]['contentDetails']
                
                return {
                    'view_count': int(stats.get('viewCount', 0)),
                    'like_count': int(stats.get('likeCount', 0)),
                    'comment_count': int(stats.get('commentCount', 0)),
                    'duration': content_details.get('duration', ''),
                    'engagement_rate': self._calculate_engagement_rate(stats)
                }
        except Exception as e:
            logger.error(f"Error getting video statistics for {video_id}: {e}")
        
        return {
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'duration': '',
            'engagement_rate': 0.0
        }
    
    def _calculate_engagement_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate engagement rate (likes + comments) / views."""
        try:
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            
            if views > 0:
                return round((likes + comments) / views * 100, 2)
        except:
            pass
        
        return 0.0
    
    async def get_channel_info(
        self,
        channel_id: Optional[str] = None,
        channel_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get channel information and statistics.
        
        Args:
            channel_id: YouTube channel ID
            channel_username: YouTube channel username
            
        Returns:
            Channel information and statistics
        """
        if not self.service:
            raise Exception("YouTube Data API not configured")
        
        if not channel_id and not channel_username:
            raise Exception("Either channel_id or channel_username must be provided")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_channel_info_sync, 
                channel_id, 
                channel_username
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            raise Exception(f"Failed to get channel info: {e}")
    
    def _get_channel_info_sync(self, channel_id: Optional[str], channel_username: Optional[str]) -> Dict[str, Any]:
        """Synchronous method to get channel info."""
        if channel_id:
            request = self.service.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            )
        else:
            request = self.service.channels().list(
                part='snippet,statistics,contentDetails',
                forUsername=channel_username
            )
        
        response = request.execute()
        
        if not response['items']:
            raise Exception("Channel not found")
        
        channel = response['items'][0]
        snippet = channel['snippet']
        statistics = channel['statistics']
        
        return {
            'channel_id': channel['id'],
            'title': snippet['title'],
            'description': snippet['description'][:500] + '...' if len(snippet['description']) > 500 else snippet['description'],
            'published_at': snippet['publishedAt'],
            'country': snippet.get('country', ''),
            'custom_url': snippet.get('customUrl', ''),
            'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'statistics': {
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0))
            },
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_trending_videos(
        self,
        category_id: Optional[str] = None,
        region_code: str = 'US',
        max_results: int = 25
    ) -> Dict[str, Any]:
        """
        Get trending videos.
        
        Args:
            category_id: Video category ID (optional)
            region_code: Region code (US, GB, CA, etc.)
            max_results: Maximum number of results
            
        Returns:
            Trending videos data
        """
        if not self.service:
            raise Exception("YouTube Data API not configured")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_trending_videos_sync, 
                category_id, 
                region_code, 
                max_results
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting trending videos: {e}")
            raise Exception(f"Failed to get trending videos: {e}")
    
    def _get_trending_videos_sync(self, category_id: Optional[str], region_code: str, max_results: int) -> Dict[str, Any]:
        """Synchronous method to get trending videos."""
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'maxResults': min(max_results, 50)
        }
        
        if category_id:
            params['videoCategoryId'] = category_id
        
        request = self.service.videos().list(**params)
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            snippet = item['snippet']
            statistics = item['statistics']
            
            videos.append({
                'video_id': item['id'],
                'title': snippet['title'],
                'description': snippet['description'][:500] + '...' if len(snippet['description']) > 500 else snippet['description'],
                'published_at': snippet['publishedAt'],
                'channel_title': snippet['channelTitle'],
                'category_id': snippet['categoryId'],
                'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'url': f'https://www.youtube.com/watch?v={item["id"]}',
                'statistics': {
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'engagement_rate': self._calculate_engagement_rate(statistics)
                }
            })
        
        return {
            'region_code': region_code,
            'category_id': category_id,
            'total_results': len(videos),
            'videos': videos,
            'fetched_at': datetime.now().isoformat()
        }
    
    async def analyze_video_seo(
        self,
        video_id: str
    ) -> Dict[str, Any]:
        """
        Analyze video SEO factors.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video SEO analysis
        """
        if not self.service:
            raise Exception("YouTube Data API not configured")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._analyze_video_seo_sync, 
                video_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing video SEO: {e}")
            raise Exception(f"Failed to analyze video SEO: {e}")
    
    def _analyze_video_seo_sync(self, video_id: str) -> Dict[str, Any]:
        """Synchronous method to analyze video SEO."""
        request = self.service.videos().list(
            part='snippet,statistics,contentDetails,status',
            id=video_id
        )
        
        response = request.execute()
        
        if not response['items']:
            raise Exception("Video not found")
        
        video = response['items'][0]
        snippet = video['snippet']
        statistics = video['statistics']
        content_details = video['contentDetails']
        
        # SEO Analysis
        title = snippet['title']
        description = snippet['description']
        tags = snippet.get('tags', [])
        
        seo_analysis = {
            'title_length': len(title),
            'title_optimal': 60 <= len(title) <= 100,
            'description_length': len(description),
            'description_optimal': len(description) >= 125,
            'tags_count': len(tags),
            'tags_optimal': 5 <= len(tags) <= 15,
            'has_custom_thumbnail': True,  # API doesn't provide this info
            'engagement_metrics': {
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'engagement_rate': self._calculate_engagement_rate(statistics)
            }
        }
        
        # SEO Score calculation
        score_factors = [
            seo_analysis['title_optimal'],
            seo_analysis['description_optimal'],
            seo_analysis['tags_optimal'],
            seo_analysis['engagement_metrics']['engagement_rate'] > 2.0
        ]
        
        seo_score = (sum(score_factors) / len(score_factors)) * 100
        
        return {
            'video_id': video_id,
            'title': title,
            'description': description[:200] + '...' if len(description) > 200 else description,
            'tags': tags,
            'seo_analysis': seo_analysis,
            'seo_score': round(seo_score, 1),
            'recommendations': self._generate_seo_recommendations(seo_analysis),
            'fetched_at': datetime.now().isoformat()
        }
    
    def _generate_seo_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate SEO recommendations based on analysis."""
        recommendations = []
        
        if not analysis['title_optimal']:
            if analysis['title_length'] < 60:
                recommendations.append("Title is too short. Aim for 60-100 characters for better SEO.")
            else:
                recommendations.append("Title is too long. Keep it under 100 characters to avoid truncation.")
        
        if not analysis['description_optimal']:
            recommendations.append("Description should be at least 125 characters for better SEO.")
        
        if not analysis['tags_optimal']:
            if analysis['tags_count'] < 5:
                recommendations.append("Add more tags. Use 5-15 relevant tags for better discoverability.")
            else:
                recommendations.append("Too many tags can be seen as spam. Keep it between 5-15 tags.")
        
        if analysis['engagement_metrics']['engagement_rate'] < 2.0:
            recommendations.append("Low engagement rate. Encourage likes, comments, and shares to improve reach.")
        
        if not recommendations:
            recommendations.append("Video SEO looks good! Keep creating quality content.")
        
        return recommendations


# Global instance
youtube_client = YouTubeDataClient()
