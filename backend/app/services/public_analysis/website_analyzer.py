"""
Public Website Analysis Engine

This service provides comprehensive website analysis for ANY public website
using global API keys. No user authentication required.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from app.services.pagespeed_insights import pagespeed_client
from app.services.serpapi import serp_client
from app.services.programmable_search import search_client
from app.services.openai_service import openai_client
from app.services.social_media import social_media_client

logger = logging.getLogger(__name__)


class PublicWebsiteAnalyzer:
    """
    Analyze any public website using global API keys.
    Perfect for competitor research and general SEO audits.
    """
    
    def __init__(self):
        self.pagespeed = pagespeed_client
        self.serp = serp_client
        self.search = search_client
        self.ai = openai_client
        self.social = social_media_client
    
    async def analyze_website_comprehensive(
        self,
        domain: str,
        target_keywords: Optional[List[str]] = None,
        include_social: bool = True,
        include_competitors: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of any website.
        
        Args:
            domain: Website domain to analyze (e.g., "example.com")
            target_keywords: Keywords to check rankings for
            include_social: Include social media analysis
            include_competitors: Include competitor comparison
            
        Returns:
            Complete website analysis report
        """
        logger.info(f"Starting comprehensive analysis for {domain}")
        
        # Ensure domain is clean (remove http/https)
        clean_domain = self._clean_domain(domain)
        website_url = f"https://{clean_domain}"
        
        analysis_results = {
            'domain': clean_domain,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_public',
            'technical_seo': {},
            'performance': {},
            'rankings': {},
            'content_analysis': {},
            'social_presence': {},
            'competitor_analysis': {},
            'ai_insights': {}
        }
        
        # Run analyses in parallel for speed
        tasks = []
        
        # 1. Technical Performance Analysis
        tasks.append(self._analyze_performance(website_url))
        
        # 2. SEO Rankings Analysis
        if target_keywords:
            tasks.append(self._analyze_rankings(clean_domain, target_keywords))
        else:
            # Use common SEO keywords if none provided
            tasks.append(self._analyze_rankings(clean_domain, [clean_domain, f"{clean_domain} review"]))
        
        # 3. Content Analysis
        tasks.append(self._analyze_content_strategy(clean_domain))
        
        # 4. Social Media Presence
        if include_social:
            tasks.append(self._analyze_social_presence(clean_domain))
        
        # Execute all analyses
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            analysis_results['performance'] = results[0] if not isinstance(results[0], Exception) else {'error': str(results[0])}
            analysis_results['rankings'] = results[1] if not isinstance(results[1], Exception) else {'error': str(results[1])}
            analysis_results['content_analysis'] = results[2] if not isinstance(results[2], Exception) else {'error': str(results[2])}
            
            if include_social and len(results) > 3:
                analysis_results['social_presence'] = results[3] if not isinstance(results[3], Exception) else {'error': str(results[3])}
            
            # 5. AI-powered insights (after other data is collected)
            analysis_results['ai_insights'] = await self._generate_ai_insights(analysis_results)
            
            # 6. Competitor analysis (optional)
            if include_competitors and target_keywords:
                analysis_results['competitor_analysis'] = await self._analyze_competitors(target_keywords[0])
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            analysis_results['error'] = str(e)
        
        return analysis_results
    
    async def _analyze_performance(self, website_url: str) -> Dict[str, Any]:
        """Analyze website performance using PageSpeed Insights."""
        try:
            result = await self.pagespeed.analyze_url(website_url)
            return {
                'performance_score': result.get('performance_score'),
                'accessibility_score': result.get('accessibility_score'),
                'best_practices_score': result.get('best_practices_score'),
                'seo_score': result.get('seo_score'),
                'core_web_vitals': result.get('core_web_vitals', {}),
                'opportunities': result.get('opportunities', []),
                'diagnostics': result.get('diagnostics', [])
            }
        except Exception as e:
            logger.error(f"Performance analysis error: {e}")
            return {'error': str(e)}
    
    async def _analyze_rankings(self, domain: str, keywords: List[str]) -> Dict[str, Any]:
        """Analyze search rankings for target keywords."""
        try:
            ranking_results = {}
            
            for keyword in keywords[:5]:  # Limit to 5 keywords to avoid rate limits
                serp_data = await self.serp.advanced_serp_analysis(keyword)
                
                if 'error' not in serp_data:
                    # Find domain position in results
                    position = self._find_domain_position(serp_data, domain)
                    ranking_results[keyword] = {
                        'position': position,
                        'serp_features': serp_data.get('serp_features', []),
                        'competition_level': serp_data.get('competition_analysis', {}).get('level', 'unknown')
                    }
                else:
                    ranking_results[keyword] = {'error': serp_data['error']}
            
            return ranking_results
            
        except Exception as e:
            logger.error(f"Rankings analysis error: {e}")
            return {'error': str(e)}
    
    async def _analyze_content_strategy(self, domain: str) -> Dict[str, Any]:
        """Analyze content strategy using search results."""
        try:
            # Search for domain content
            search_results = await self.search.search_keywords(f"site:{domain}", num_results=10)
            
            if 'error' not in search_results:
                pages_found = len(search_results.get('results', []))
                content_types = self._categorize_content(search_results.get('results', []))
                
                return {
                    'indexed_pages': pages_found,
                    'content_types': content_types,
                    'top_content': search_results.get('results', [])[:5]
                }
            else:
                return {'error': search_results['error']}
                
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return {'error': str(e)}
    
    async def _analyze_social_presence(self, domain: str) -> Dict[str, Any]:
        """Analyze social media presence."""
        try:
            brand_name = domain.split('.')[0]  # Extract brand name from domain
            
            # Search for brand mentions
            social_data = await self.social.get_brand_mentions(brand_name)
            
            return {
                'brand_mentions': social_data.get('summary', {}).get('total_mentions', 0),
                'social_signals_score': social_data.get('summary', {}).get('social_signals_score', 0),
                'platforms_active': social_data.get('summary', {}).get('platforms_active', 0),
                'recommendation': social_data.get('summary', {}).get('recommendation', '')
            }
            
        except Exception as e:
            logger.error(f"Social analysis error: {e}")
            return {'error': str(e)}
    
    async def _generate_ai_insights(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered insights from analysis data."""
        try:
            # Create prompt from analysis data
            prompt = self._create_analysis_prompt(analysis_data)
            
            ai_response = await self.ai.generate_seo_insights(
                prompt,
                analysis_data.get('domain', ''),
                analysis_data.get('rankings', {}).keys()
            )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"AI insights error: {e}")
            return {'error': str(e)}
    
    async def _analyze_competitors(self, keyword: str) -> Dict[str, Any]:
        """Analyze top competitors for a keyword."""
        try:
            serp_data = await self.serp.advanced_serp_analysis(keyword)
            
            if 'error' not in serp_data:
                competitors = []
                organic_results = serp_data.get('organic_results', [])[:5]
                
                for result in organic_results:
                    competitor_domain = self._extract_domain(result.get('link', ''))
                    competitors.append({
                        'domain': competitor_domain,
                        'title': result.get('title', ''),
                        'position': result.get('position', 0),
                        'url': result.get('link', '')
                    })
                
                return {
                    'top_competitors': competitors,
                    'analyzed_keyword': keyword,
                    'serp_features_present': serp_data.get('serp_features', [])
                }
            else:
                return {'error': serp_data['error']}
                
        except Exception as e:
            logger.error(f"Competitor analysis error: {e}")
            return {'error': str(e)}
    
    def _clean_domain(self, domain: str) -> str:
        """Clean domain string (remove protocol, www, trailing slashes)."""
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.replace('www.', '')
        domain = domain.rstrip('/')
        return domain
    
    def _find_domain_position(self, serp_data: Dict[str, Any], target_domain: str) -> Optional[int]:
        """Find domain position in SERP results."""
        organic_results = serp_data.get('organic_results', [])
        
        for result in organic_results:
            result_domain = self._extract_domain(result.get('link', ''))
            if target_domain in result_domain or result_domain in target_domain:
                return result.get('position', 0)
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ''
        
        # Remove protocol
        url = url.replace('https://', '').replace('http://', '')
        # Get domain part
        domain = url.split('/')[0]
        # Remove www
        domain = domain.replace('www.', '')
        
        return domain
    
    def _categorize_content(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize content types based on URLs and titles."""
        content_types = {
            'blog_posts': 0,
            'product_pages': 0,
            'landing_pages': 0,
            'other': 0
        }
        
        for result in results:
            url = result.get('link', '').lower()
            title = result.get('title', '').lower()
            
            if 'blog' in url or 'news' in url or 'article' in url:
                content_types['blog_posts'] += 1
            elif 'product' in url or 'shop' in url or 'buy' in url:
                content_types['product_pages'] += 1
            elif len(url.split('/')) <= 4:  # Likely a main/landing page
                content_types['landing_pages'] += 1
            else:
                content_types['other'] += 1
        
        return content_types
    
    def _create_analysis_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """Create AI prompt from analysis data."""
        domain = analysis_data.get('domain', 'website')
        performance = analysis_data.get('performance', {})
        rankings = analysis_data.get('rankings', {})
        
        prompt = f"""
        Analyze this SEO data for {domain} and provide actionable insights:
        
        Performance Scores:
        - Performance: {performance.get('performance_score', 'N/A')}
        - SEO: {performance.get('seo_score', 'N/A')}
        - Accessibility: {performance.get('accessibility_score', 'N/A')}
        
        Rankings: {list(rankings.keys())}
        
        Provide specific, actionable SEO recommendations.
        """
        
        return prompt


# Global instance for public website analysis
public_analyzer = PublicWebsiteAnalyzer()
