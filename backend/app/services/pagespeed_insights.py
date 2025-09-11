"""
PageSpeed Insights API Integration.

This module provides integration with Google PageSpeed Insights API to fetch
real Core Web Vitals and website performance data.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PageSpeedInsightsClient:
    """Client for Google PageSpeed Insights API."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_PAGESPEED_API_KEY
        self.base_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    async def analyze_url(
        self,
        url: str,
        strategy: str = 'desktop',
        categories: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a URL with PageSpeed Insights.
        
        Args:
            url: URL to analyze
            strategy: 'desktop' or 'mobile'
            categories: List of categories to analyze
            
        Returns:
            PageSpeed analysis results
        """
        if not self.api_key:
            raise Exception("Google PageSpeed API key not configured")
        
        try:
            params = {
                'url': url,
                'strategy': strategy,
                'key': self.api_key
            }
            
            if categories:
                params['category'] = categories
            else:
                params['category'] = ['PERFORMANCE', 'ACCESSIBILITY', 'BEST_PRACTICES', 'SEO']
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"PageSpeed Insights API error: {e}")
            raise Exception(f"Failed to analyze URL with PageSpeed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing URL: {e}")
            raise
    
    async def get_core_web_vitals(
        self,
        url: str,
        strategy: str = 'desktop'
    ) -> Dict[str, Any]:
        """
        Get Core Web Vitals for a URL.
        
        Args:
            url: URL to analyze
            strategy: 'desktop' or 'mobile'
            
        Returns:
            Core Web Vitals data
        """
        try:
            result = await self.analyze_url(url, strategy, ['PERFORMANCE'])
            
            # Extract Core Web Vitals from the response
            lighthouse_result = result.get('lighthouseResult', {})
            audits = lighthouse_result.get('audits', {})
            
            # Extract Core Web Vitals metrics
            lcp_audit = audits.get('largest-contentful-paint', {})
            fid_audit = audits.get('max-potential-fid', {})  # FID approximation
            cls_audit = audits.get('cumulative-layout-shift', {})
            ttfb_audit = audits.get('server-response-time', {})
            
            # Get metric values
            lcp = lcp_audit.get('numericValue', 0) / 1000  # Convert to seconds
            fid = fid_audit.get('numericValue', 0)  # Already in milliseconds
            cls = cls_audit.get('numericValue', 0)
            ttfb = ttfb_audit.get('numericValue', 0)
            
            # Determine status based on Core Web Vitals thresholds
            lcp_status = 'good' if lcp <= 2.5 else 'needs-improvement' if lcp <= 4.0 else 'poor'
            fid_status = 'good' if fid <= 100 else 'needs-improvement' if fid <= 300 else 'poor'
            cls_status = 'good' if cls <= 0.1 else 'needs-improvement' if cls <= 0.25 else 'poor'
            ttfb_status = 'good' if ttfb <= 600 else 'needs-improvement' if ttfb <= 1500 else 'poor'
            
            # Overall status (worst of all metrics)
            statuses = [lcp_status, fid_status, cls_status, ttfb_status]
            if 'poor' in statuses:
                overall_status = 'poor'
            elif 'needs-improvement' in statuses:
                overall_status = 'needs-improvement'
            else:
                overall_status = 'good'
            
            return {
                'lcp': round(lcp, 2),
                'fid': round(fid),
                'cls': round(cls, 3),
                'ttfb': round(ttfb),
                'status': overall_status,
                'measured_at': lighthouse_result.get('fetchTime', ''),
                'device_type': strategy,
                'url': url,
                'metrics_detail': {
                    'lcp_assessment': lcp_status,
                    'fid_assessment': fid_status,
                    'cls_assessment': cls_status,
                    'ttfb_assessment': ttfb_status
                },
                'performance_score': lighthouse_result.get('categories', {}).get('performance', {}).get('score', 0) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting Core Web Vitals: {e}")
            raise
    
    async def get_lighthouse_scores(
        self,
        url: str,
        strategy: str = 'desktop'
    ) -> Dict[str, Any]:
        """
        Get Lighthouse scores for all categories.
        
        Args:
            url: URL to analyze
            strategy: 'desktop' or 'mobile'
            
        Returns:
            Lighthouse scores data
        """
        try:
            result = await self.analyze_url(url, strategy)
            
            lighthouse_result = result.get('lighthouseResult', {})
            categories = lighthouse_result.get('categories', {})
            
            scores = {}
            for category_name, category_data in categories.items():
                scores[category_name] = {
                    'score': round(category_data.get('score', 0) * 100),
                    'title': category_data.get('title', category_name)
                }
            
            return {
                'url': url,
                'strategy': strategy,
                'scores': scores,
                'fetch_time': lighthouse_result.get('fetchTime', ''),
                'user_agent': lighthouse_result.get('userAgent', '')
            }
            
        except Exception as e:
            logger.error(f"Error getting Lighthouse scores: {e}")
            raise
    
    async def get_page_insights(
        self,
        url: str,
        strategy: str = 'desktop'
    ) -> Dict[str, Any]:
        """
        Get comprehensive page insights including opportunities and diagnostics.
        
        Args:
            url: URL to analyze
            strategy: 'desktop' or 'mobile'
            
        Returns:
            Page insights data
        """
        try:
            result = await self.analyze_url(url, strategy)
            
            lighthouse_result = result.get('lighthouseResult', {})
            audits = lighthouse_result.get('audits', {})
            
            # Extract opportunities (performance improvements)
            opportunities = []
            for audit_id, audit_data in audits.items():
                if audit_data.get('scoreDisplayMode') == 'numeric' and audit_data.get('score', 1) < 1:
                    potential_savings = audit_data.get('details', {}).get('overallSavingsMs', 0)
                    if potential_savings > 0:
                        opportunities.append({
                            'title': audit_data.get('title', audit_id),
                            'description': audit_data.get('description', ''),
                            'potential_savings_ms': potential_savings,
                            'potential_savings_bytes': audit_data.get('details', {}).get('overallSavingsBytes', 0),
                            'score': audit_data.get('score', 0)
                        })
            
            # Sort by potential savings
            opportunities.sort(key=lambda x: x['potential_savings_ms'], reverse=True)
            
            # Extract diagnostics
            diagnostics = []
            for audit_id, audit_data in audits.items():
                if audit_data.get('scoreDisplayMode') == 'informative':
                    diagnostics.append({
                        'title': audit_data.get('title', audit_id),
                        'description': audit_data.get('description', ''),
                        'display_value': audit_data.get('displayValue', ''),
                        'score': audit_data.get('score')
                    })
            
            return {
                'url': url,
                'strategy': strategy,
                'opportunities': opportunities[:10],  # Top 10 opportunities
                'diagnostics': diagnostics[:15],  # Top 15 diagnostics
                'fetch_time': lighthouse_result.get('fetchTime', '')
            }
            
        except Exception as e:
            logger.error(f"Error getting page insights: {e}")
            raise


# Global instance
pagespeed_client = PageSpeedInsightsClient()
