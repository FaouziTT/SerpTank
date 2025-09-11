"""
Response processors for OpenAI service.

This module contains functions to process and structure responses
from the OpenAI API for various use cases.
"""
import re
from typing import Dict, Any, List, Optional


def process_content_response(
    response_data: Dict[str, Any],
    content_type: str,
    target_keywords: Optional[List[str]] = None,
    model: str = "gpt-4"
) -> Dict[str, Any]:
    """Process OpenAI response for content generation."""
    content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    return {
        "content": content,
        "content_type": content_type,
        "target_keywords": target_keywords or [],
        "word_count": len(content.split()),
        "generated_by": "OpenAI",
        "model_used": model,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        },
        "seo_score": calculate_seo_score(content, target_keywords or []),
        "recommendations": generate_content_recommendations(content, target_keywords or [])
    }


def process_gap_analysis_response(
    response_data: Dict[str, Any],
    target_keywords: List[str]
) -> Dict[str, Any]:
    """Process OpenAI response for content gap analysis."""
    analysis = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    return {
        "analysis": analysis,
        "target_keywords": target_keywords,
        "opportunities": extract_opportunities(analysis),
        "priority_topics": extract_priority_items(analysis),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


def process_sge_optimization_response(
    response_data: Dict[str, Any],
    current_url: str
) -> Dict[str, Any]:
    """Process OpenAI response for SGE optimization."""
    optimization = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    return {
        "url": current_url,
        "optimization_suggestions": optimization,
        "key_improvements": extract_key_improvements(optimization),
        "sge_readiness_score": calculate_sge_readiness_score(optimization),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


def process_insights_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process OpenAI response for SEO insights."""
    insights = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    return {
        "insights": insights,
        "action_items": extract_action_items(insights),
        "priority": determine_priority(insights),
        "impact_areas": identify_impact_areas(insights),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


def process_brief_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process OpenAI response for content brief generation."""
    brief = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    # Extract sections from the brief
    sections = extract_brief_sections(brief)
    
    return {
        "full_brief": brief,
        "sections": sections,
        "word_count_estimate": estimate_content_length(brief),
        "research_requirements": extract_research_requirements(brief),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


def process_enhancement_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process OpenAI response for content enhancement."""
    enhancement = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = response_data.get("usage", {})
    
    return {
        "enhancement_suggestions": enhancement,
        "priority_changes": extract_priority_changes(enhancement),
        "estimated_impact": estimate_enhancement_impact(enhancement),
        "implementation_difficulty": assess_implementation_difficulty(enhancement),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


# Helper functions

def calculate_seo_score(content: str, keywords: List[str]) -> int:
    """Calculate basic SEO score based on keyword usage and content structure."""
    if not content:
        return 0
    
    score = 50  # Base score
    content_lower = content.lower()
    
    # Keyword presence (up to 30 points)
    for keyword in keywords[:5]:  # Check top 5 keywords
        if keyword.lower() in content_lower:
            score += 6
    
    # Content length (up to 10 points)
    word_count = len(content.split())
    if word_count >= 300:
        score += 5
    if word_count >= 600:
        score += 5
    
    # Headers presence (up to 10 points)
    if re.search(r'#{1,6}\s', content) or re.search(r'<h[1-6]>', content):
        score += 10
    
    return min(score, 100)


def generate_content_recommendations(content: str, keywords: List[str]) -> List[str]:
    """Generate basic content recommendations."""
    recommendations = []
    content_lower = content.lower()
    word_count = len(content.split())
    
    # Check keyword density
    for keyword in keywords:
        keyword_count = content_lower.count(keyword.lower())
        if keyword_count == 0:
            recommendations.append(f"Include the target keyword '{keyword}' in your content")
        elif keyword_count > word_count * 0.03:  # Over 3% density
            recommendations.append(f"Reduce the usage of '{keyword}' to avoid keyword stuffing")
    
    # Content length recommendations
    if word_count < 300:
        recommendations.append("Increase content length to at least 300 words for better SEO")
    
    # Structure recommendations
    if not re.search(r'#{1,6}\s|<h[1-6]>', content):
        recommendations.append("Add headers (H1-H6) to improve content structure")
    
    return recommendations


def extract_opportunities(analysis: str) -> List[str]:
    """Extract content opportunities from analysis text."""
    opportunities = []
    
    # Look for bullet points or numbered lists
    pattern = r'(?:^|\n)[\-\*•]\s*(.+?)(?=\n|$)'
    matches = re.findall(pattern, analysis, re.MULTILINE)
    opportunities.extend(matches[:10])  # Limit to 10 items
    
    # Look for phrases indicating opportunities
    opportunity_patterns = [
        r'opportunity:?\s*(.+?)(?:\.|$)',
        r'consider:?\s*(.+?)(?:\.|$)',
        r'gap:?\s*(.+?)(?:\.|$)'
    ]
    
    for pattern in opportunity_patterns:
        matches = re.findall(pattern, analysis, re.IGNORECASE)
        opportunities.extend(matches[:3])
    
    return list(set(opportunities))[:10]  # Remove duplicates and limit


def extract_priority_items(analysis: str) -> List[str]:
    """Extract priority items from analysis."""
    priority_items = []
    
    # Look for priority indicators
    priority_patterns = [
        r'high priority:?\s*(.+?)(?:\.|$)',
        r'urgent:?\s*(.+?)(?:\.|$)',
        r'important:?\s*(.+?)(?:\.|$)',
        r'focus on:?\s*(.+?)(?:\.|$)'
    ]
    
    for pattern in priority_patterns:
        matches = re.findall(pattern, analysis, re.IGNORECASE)
        priority_items.extend(matches)
    
    return list(set(priority_items))[:5]


def extract_key_improvements(optimization: str) -> List[str]:
    """Extract key improvements from SGE optimization text."""
    improvements = []
    
    # Look for improvement indicators
    improvement_patterns = [
        r'improve:?\s*(.+?)(?:\.|$)',
        r'optimize:?\s*(.+?)(?:\.|$)',
        r'enhance:?\s*(.+?)(?:\.|$)',
        r'add:?\s*(.+?)(?:\.|$)'
    ]
    
    for pattern in improvement_patterns:
        matches = re.findall(pattern, optimization, re.IGNORECASE)
        improvements.extend(matches[:3])
    
    return list(set(improvements))[:10]


def extract_action_items(insights: str) -> List[str]:
    """Extract actionable items from insights."""
    action_items = []
    
    # Look for action verbs
    action_patterns = [
        r'(?:should|must|need to|have to)\s+(.+?)(?:\.|$)',
        r'(?:implement|create|add|update|fix)\s+(.+?)(?:\.|$)'
    ]
    
    for pattern in action_patterns:
        matches = re.findall(pattern, insights, re.IGNORECASE)
        action_items.extend(matches)
    
    return list(set(action_items))[:10]


def calculate_sge_readiness_score(optimization: str) -> int:
    """Calculate SGE readiness score based on optimization suggestions."""
    score = 50  # Base score
    
    # Check for key SGE factors
    sge_factors = [
        'structured data', 'schema', 'clear answers', 'authoritative',
        'expert', 'trustworth', 'comprehensive', 'well-organized'
    ]
    
    optimization_lower = optimization.lower()
    for factor in sge_factors:
        if factor in optimization_lower:
            score += 6
    
    return min(score, 100)


def determine_priority(insights: str) -> str:
    """Determine priority level from insights."""
    insights_lower = insights.lower()
    
    high_priority_indicators = ['critical', 'urgent', 'immediate', 'severe']
    medium_priority_indicators = ['important', 'significant', 'notable']
    
    for indicator in high_priority_indicators:
        if indicator in insights_lower:
            return 'high'
    
    for indicator in medium_priority_indicators:
        if indicator in insights_lower:
            return 'medium'
    
    return 'low'


def identify_impact_areas(insights: str) -> List[str]:
    """Identify areas of impact from insights."""
    areas = []
    
    impact_keywords = {
        'ranking': ['ranking', 'position', 'serp'],
        'traffic': ['traffic', 'visitors', 'sessions'],
        'conversion': ['conversion', 'ctr', 'click-through'],
        'user_experience': ['ux', 'user experience', 'usability'],
        'technical': ['technical', 'performance', 'speed'],
        'content': ['content', 'quality', 'relevance']
    }
    
    insights_lower = insights.lower()
    for area, keywords in impact_keywords.items():
        for keyword in keywords:
            if keyword in insights_lower:
                areas.append(area)
                break
    
    return list(set(areas))


def extract_brief_sections(brief: str) -> Dict[str, str]:
    """Extract sections from a content brief."""
    sections = {}
    
    # Common section headers
    section_patterns = {
        'target_audience': r'target audience:?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        'outline': r'(?:outline|structure):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        'key_points': r'key (?:points|topics):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        'seo_guidelines': r'seo (?:guidelines|optimization):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
        'tone_style': r'(?:tone|style):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
    }
    
    for section, pattern in section_patterns.items():
        match = re.search(pattern, brief, re.IGNORECASE | re.DOTALL)
        if match:
            sections[section] = match.group(1).strip()
    
    return sections


def extract_research_requirements(brief: str) -> List[str]:
    """Extract research requirements from brief."""
    requirements = []
    
    research_patterns = [
        r'research:?\s*(.+?)(?:\.|$)',
        r'investigate:?\s*(.+?)(?:\.|$)',
        r'analyze:?\s*(.+?)(?:\.|$)'
    ]
    
    for pattern in research_patterns:
        matches = re.findall(pattern, brief, re.IGNORECASE)
        requirements.extend(matches)
    
    return list(set(requirements))[:5]


def estimate_content_length(brief: str) -> int:
    """Estimate recommended content length from brief."""
    # Look for word count mentions
    word_count_match = re.search(r'(\d+)\s*(?:words|word)', brief, re.IGNORECASE)
    if word_count_match:
        return int(word_count_match.group(1))
    
    # Default based on content type mentions
    if 'comprehensive' in brief.lower() or 'detailed' in brief.lower():
        return 2000
    elif 'brief' in brief.lower() or 'concise' in brief.lower():
        return 500
    
    return 1000  # Default


def extract_priority_changes(enhancement: str) -> List[str]:
    """Extract priority changes from enhancement suggestions."""
    changes = []
    
    priority_patterns = [
        r'priority:?\s*(.+?)(?:\.|$)',
        r'first:?\s*(.+?)(?:\.|$)',
        r'immediately:?\s*(.+?)(?:\.|$)'
    ]
    
    for pattern in priority_patterns:
        matches = re.findall(pattern, enhancement, re.IGNORECASE)
        changes.extend(matches)
    
    return list(set(changes))[:5]


def estimate_enhancement_impact(enhancement: str) -> str:
    """Estimate the impact of enhancement suggestions."""
    enhancement_lower = enhancement.lower()
    
    high_impact_indicators = ['significant', 'major', 'substantial', 'dramatic']
    medium_impact_indicators = ['moderate', 'notable', 'improvement']
    
    for indicator in high_impact_indicators:
        if indicator in enhancement_lower:
            return 'high'
    
    for indicator in medium_impact_indicators:
        if indicator in enhancement_lower:
            return 'medium'
    
    return 'low'


def assess_implementation_difficulty(enhancement: str) -> str:
    """Assess the difficulty of implementing enhancements."""
    enhancement_lower = enhancement.lower()
    
    easy_indicators = ['simple', 'quick', 'easy', 'minor']
    hard_indicators = ['complex', 'extensive', 'major overhaul', 'significant changes']
    
    for indicator in hard_indicators:
        if indicator in enhancement_lower:
            return 'hard'
    
    for indicator in easy_indicators:
        if indicator in enhancement_lower:
            return 'easy'
    
    return 'medium'