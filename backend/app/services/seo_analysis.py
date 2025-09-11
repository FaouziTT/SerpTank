"""
SEO Analysis Service.

This module provides comprehensive SEO analysis including
on-page optimization, technical SEO, and content analysis.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import re

import httpx
from bs4 import BeautifulSoup
import advertools as adv

from app.core.config import settings

logger = logging.getLogger(__name__)


class SEOAnalysisService:
    """Service for comprehensive SEO analysis."""
    
    def __init__(self):
        self.session = None
    
    async def analyze_page(self, url: str) -> Dict[str, Any]:
        """
        Perform comprehensive SEO analysis of a page.
        
        Args:
            url: URL to analyze
            
        Returns:
            SEO analysis results
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analyze different SEO aspects
            analysis = {
                'url': url,
                'title_analysis': self._analyze_title(soup),
                'meta_analysis': self._analyze_meta_tags(soup),
                'heading_analysis': self._analyze_headings(soup),
                'content_analysis': self._analyze_content(soup, html_content),
                'link_analysis': await self._analyze_links(soup, url),
                'image_analysis': self._analyze_images(soup),
                'technical_analysis': self._analyze_technical(soup, response),
                'performance_analysis': await self._analyze_performance(url)
            }
            
            # Calculate overall SEO score
            analysis['seo_score'] = self._calculate_seo_score(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing page {url}: {e}")
            raise
    
    def _analyze_title(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze page title."""
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else ''
        
        return {
            'title': title,
            'length': len(title),
            'is_present': bool(title),
            'is_optimal_length': 30 <= len(title) <= 60,
            'recommendations': self._get_title_recommendations(title)
        }
    
    def _analyze_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze meta tags."""
        meta_description = ''
        meta_keywords = ''
        robots = ''
        
        # Get meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_description = meta_desc.get('content', '')
        
        # Get meta keywords
        meta_keys = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keys:
            meta_keywords = meta_keys.get('content', '')
        
        # Get robots meta
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta:
            robots = robots_meta.get('content', '')
        
        return {
            'meta_description': {
                'content': meta_description,
                'length': len(meta_description),
                'is_present': bool(meta_description),
                'is_optimal_length': 120 <= len(meta_description) <= 160
            },
            'meta_keywords': {
                'content': meta_keywords,
                'is_present': bool(meta_keywords)
            },
            'robots': {
                'content': robots,
                'is_present': bool(robots)
            }
        }
    
    def _analyze_headings(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze heading structure."""
        headings = {
            'h1': [h.text.strip() for h in soup.find_all('h1')],
            'h2': [h.text.strip() for h in soup.find_all('h2')],
            'h3': [h.text.strip() for h in soup.find_all('h3')],
            'h4': [h.text.strip() for h in soup.find_all('h4')],
            'h5': [h.text.strip() for h in soup.find_all('h5')],
            'h6': [h.text.strip() for h in soup.find_all('h6')]
        }
        
        h1_count = len(headings['h1'])
        
        return {
            'headings': headings,
            'h1_count': h1_count,
            'has_h1': h1_count > 0,
            'has_single_h1': h1_count == 1,
            'heading_structure_score': self._calculate_heading_score(headings)
        }
    
    def _analyze_content(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Analyze page content."""
        # Extract text content
        text_content = soup.get_text()
        word_count = len(text_content.split())
        
        # Calculate text-to-HTML ratio
        html_size = len(html_content)
        text_size = len(text_content)
        text_html_ratio = (text_size / html_size) * 100 if html_size > 0 else 0
        
        # Extract keywords (simple approach)
        keywords = self._extract_keywords(text_content)
        
        return {
            'word_count': word_count,
            'text_html_ratio': round(text_html_ratio, 2),
            'readability_score': self._calculate_readability(text_content),
            'keywords': keywords,
            'has_sufficient_content': word_count >= 300
        }
    
    async def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Analyze internal and external links."""
        links = soup.find_all('a', href=True)
        
        internal_links = []
        external_links = []
        broken_links = []
        
        base_domain = urlparse(base_url).netloc
        
        for link in links:
            href = link.get('href')
            text = link.text.strip()
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            link_domain = urlparse(full_url).netloc
            
            link_data = {
                'url': full_url,
                'text': text,
                'has_text': bool(text),
                'is_nofollow': 'nofollow' in link.get('rel', [])
            }
            
            if link_domain == base_domain or not link_domain:
                internal_links.append(link_data)
            else:
                external_links.append(link_data)
        
        return {
            'total_links': len(links),
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'internal_link_details': internal_links[:20],  # First 20
            'external_link_details': external_links[:10],  # First 10
            'broken_links': broken_links
        }
    
    def _analyze_images(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze images and alt text."""
        images = soup.find_all('img')
        
        total_images = len(images)
        images_with_alt = sum(1 for img in images if img.get('alt'))
        images_without_alt = total_images - images_with_alt
        
        image_details = []
        for img in images[:20]:  # First 20 images
            alt_text = img.get('alt', '')
            src = img.get('src', '')
            
            image_details.append({
                'src': src,
                'alt': alt_text,
                'has_alt': bool(alt_text),
                'alt_length': len(alt_text)
            })
        
        return {
            'total_images': total_images,
            'images_with_alt': images_with_alt,
            'images_without_alt': images_without_alt,
            'alt_text_coverage': round((images_with_alt / max(total_images, 1)) * 100, 1),
            'image_details': image_details
        }
    
    def _analyze_technical(self, soup: BeautifulSoup, response) -> Dict[str, Any]:
        """Analyze technical SEO aspects."""
        # Check for canonical URL
        canonical = soup.find('link', rel='canonical')
        canonical_url = canonical.get('href') if canonical else ''
        
        # Check for structured data
        structured_data = soup.find_all('script', type='application/ld+json')
        
        # Check response headers
        headers = dict(response.headers)
        
        return {
            'canonical_url': canonical_url,
            'has_canonical': bool(canonical_url),
            'structured_data_count': len(structured_data),
            'has_structured_data': len(structured_data) > 0,
            'status_code': response.status_code,
            'content_type': headers.get('content-type', ''),
            'server': headers.get('server', ''),
            'cache_control': headers.get('cache-control', ''),
            'has_ssl': response.url.startswith('https://')
        }
    
    async def _analyze_performance(self, url: str) -> Dict[str, Any]:
        """Analyze basic performance metrics."""
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            load_time = asyncio.get_event_loop().time() - start_time
            page_size = len(response.content)
            
            return {
                'load_time_seconds': round(load_time, 2),
                'page_size_bytes': page_size,
                'page_size_kb': round(page_size / 1024, 2),
                'is_fast_loading': load_time < 3.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return {
                'load_time_seconds': 0,
                'page_size_bytes': 0,
                'page_size_kb': 0,
                'is_fast_loading': False
            }
    
    def _get_title_recommendations(self, title: str) -> List[str]:
        """Get title optimization recommendations."""
        recommendations = []
        
        if not title:
            recommendations.append("Add a title tag")
        elif len(title) < 30:
            recommendations.append("Title is too short, consider expanding it")
        elif len(title) > 60:
            recommendations.append("Title is too long, consider shortening it")
        
        return recommendations
    
    def _calculate_heading_score(self, headings: Dict[str, List[str]]) -> int:
        """Calculate heading structure score."""
        score = 0
        
        # Has H1
        if headings['h1']:
            score += 30
        
        # Single H1
        if len(headings['h1']) == 1:
            score += 20
        
        # Has H2s
        if headings['h2']:
            score += 25
        
        # Proper hierarchy
        if headings['h1'] and headings['h2']:
            score += 25
        
        return score
    
    def _extract_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Extract keywords from text content."""
        try:
            # Simple keyword extraction (in production, use more sophisticated methods)
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq = {}
            
            # Count word frequency
            for word in words:
                if len(word) > 3:  # Only words longer than 3 characters
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return [{'keyword': word, 'frequency': freq} for word, freq in top_keywords]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def _calculate_readability(self, text: str) -> int:
        """Calculate basic readability score."""
        try:
            # Simple readability calculation
            sentences = len(re.split(r'[.!?]+', text))
            words = len(text.split())
            
            if sentences == 0:
                return 0
            
            avg_sentence_length = words / sentences
            
            # Simple scoring (Flesch-like)
            if avg_sentence_length <= 15:
                return 90  # Very easy
            elif avg_sentence_length <= 20:
                return 70  # Easy
            elif avg_sentence_length <= 25:
                return 50  # Fairly difficult
            else:
                return 30  # Difficult
                
        except Exception:
            return 50  # Default moderate score
    
    def _calculate_seo_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall SEO score."""
        score = 0
        
        # Title (20 points)
        if analysis['title_analysis']['is_present']:
            score += 10
        if analysis['title_analysis']['is_optimal_length']:
            score += 10
        
        # Meta description (15 points)
        if analysis['meta_analysis']['meta_description']['is_present']:
            score += 8
        if analysis['meta_analysis']['meta_description']['is_optimal_length']:
            score += 7
        
        # Headings (20 points)
        score += min(20, analysis['heading_analysis']['heading_structure_score'] * 20 / 100)
        
        # Content (20 points)
        if analysis['content_analysis']['has_sufficient_content']:
            score += 10
        if analysis['content_analysis']['readability_score'] > 50:
            score += 10
        
        # Images (10 points)
        if analysis['image_analysis']['alt_text_coverage'] > 80:
            score += 10
        elif analysis['image_analysis']['alt_text_coverage'] > 50:
            score += 5
        
        # Technical (15 points)
        if analysis['technical_analysis']['has_canonical']:
            score += 5
        if analysis['technical_analysis']['has_ssl']:
            score += 5
        if analysis['technical_analysis']['has_structured_data']:
            score += 5
        
        return min(100, score)


# Global instance
seo_analysis_service = SEOAnalysisService()
