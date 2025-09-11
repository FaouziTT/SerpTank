"""
Prompt builders for OpenAI service.

This module contains functions to build system and user prompts
for various OpenAI API interactions.
"""
from typing import List, Optional, Dict, Any


def build_seo_system_prompt(
    content_type: str,
    target_keywords: Optional[List[str]] = None,
    word_count: Optional[int] = None
) -> str:
    """Build system prompt for SEO-optimized content generation."""
    base_prompt = "You are an expert SEO content writer with deep knowledge of search engine optimization, user intent, and content marketing."
    
    if content_type == "article":
        prompt = f"{base_prompt} Create comprehensive, well-structured articles that rank well in search engines while providing genuine value to readers."
    elif content_type == "meta_description":
        prompt = f"{base_prompt} Write compelling meta descriptions that improve click-through rates while incorporating target keywords naturally."
    elif content_type == "title":
        prompt = f"{base_prompt} Create attention-grabbing, SEO-optimized titles that include target keywords and encourage clicks."
    else:
        prompt = f"{base_prompt} Create SEO-optimized {content_type} content."
    
    if target_keywords:
        prompt += f" Target keywords: {', '.join(target_keywords)}. Use these naturally throughout the content."
    
    if word_count:
        prompt += f" Target word count: approximately {word_count} words."
    
    prompt += " Focus on user intent, readability, and search engine optimization best practices."
    
    return prompt


def build_gap_analysis_system_prompt() -> str:
    """Build system prompt for content gap analysis."""
    return """You are an expert SEO analyst specializing in content gap analysis and competitive intelligence. 
    Analyze the provided content landscape and identify opportunities for new content that can capture search traffic 
    and address user needs not currently being met. Focus on actionable insights and specific content recommendations."""


def build_sge_optimization_system_prompt() -> str:
    """Build system prompt for SGE optimization."""
    return """You are an expert in Google's Search Generative Experience (SGE) and AI-powered search optimization. 
    Analyze content and provide specific recommendations to optimize for AI-generated search results. 
    Focus on structured data, clear answers, authoritative content, and features that make content more likely 
    to be featured in AI-generated summaries."""


def build_seo_insights_system_prompt() -> str:
    """Build system prompt for SEO insights generation."""
    return """You are a senior SEO strategist with expertise in technical SEO, content optimization, and search algorithms. 
    Analyze the provided data and generate actionable SEO insights. Focus on identifying opportunities, 
    highlighting issues, and providing specific recommendations for improvement. 
    Consider user intent, search trends, and competitive landscape in your analysis."""


def build_brief_system_prompt(brief_data: Dict[str, Any]) -> str:
    """Build system prompt for content brief generation."""
    content_type = brief_data.get('content_type', 'article')
    
    return f"""You are an expert content strategist specializing in creating comprehensive content briefs.
    Create a detailed content brief for a {content_type} that will rank well in search engines and provide exceptional value to readers.
    Include:
    - Target audience analysis
    - Content structure and outline
    - Key points to cover
    - SEO optimization guidelines
    - Content tone and style recommendations
    - Research requirements
    - Success metrics"""


def build_brief_user_prompt(brief_data: Dict[str, Any]) -> str:
    """Build user prompt for content brief generation."""
    topic = brief_data.get('topic', '')
    target_keywords = brief_data.get('target_keywords', [])
    target_audience = brief_data.get('target_audience', '')
    content_goals = brief_data.get('content_goals', [])
    competitor_urls = brief_data.get('competitor_urls', [])
    
    prompt = f"Create a comprehensive content brief for: {topic}\n\n"
    
    if target_keywords:
        prompt += f"Target Keywords: {', '.join(target_keywords)}\n"
    
    if target_audience:
        prompt += f"Target Audience: {target_audience}\n"
    
    if content_goals:
        prompt += f"Content Goals: {', '.join(content_goals)}\n"
    
    if competitor_urls:
        prompt += f"Competitor References: {', '.join(competitor_urls)}\n"
    
    prompt += "\nProvide a detailed brief that will guide content creation for maximum SEO impact and user value."
    
    return prompt


def build_enhancement_system_prompt(enhancement_data: Dict[str, Any]) -> str:
    """Build system prompt for content enhancement."""
    enhancement_type = enhancement_data.get('enhancement_type', 'general')
    
    base_prompt = "You are an expert content optimizer specializing in improving existing content for better search performance and user engagement."
    
    if enhancement_type == 'readability':
        return f"{base_prompt} Focus on improving readability, sentence structure, and flow while maintaining SEO value."
    elif enhancement_type == 'seo':
        return f"{base_prompt} Focus on optimizing for search engines: keyword placement, meta elements, internal linking opportunities, and semantic relevance."
    elif enhancement_type == 'engagement':
        return f"{base_prompt} Focus on increasing user engagement: add compelling hooks, improve storytelling, and enhance value propositions."
    elif enhancement_type == 'technical':
        return f"{base_prompt} Focus on technical optimization: schema markup suggestions, heading structure, and content organization."
    else:
        return f"{base_prompt} Provide comprehensive enhancement suggestions covering SEO, readability, and user value."


def build_enhancement_user_prompt(enhancement_data: Dict[str, Any]) -> str:
    """Build user prompt for content enhancement."""
    content = enhancement_data.get('content', '')
    target_keywords = enhancement_data.get('target_keywords', [])
    current_performance = enhancement_data.get('current_performance', {})
    improvement_goals = enhancement_data.get('improvement_goals', [])
    
    prompt = "Enhance the following content:\n\n"
    prompt += f"{content[:1000]}...\n\n"  # Include first 1000 chars
    
    if target_keywords:
        prompt += f"Target Keywords: {', '.join(target_keywords)}\n"
    
    if current_performance:
        prompt += f"Current Performance: "
        prompt += f"CTR: {current_performance.get('ctr', 'N/A')}, "
        prompt += f"Avg Position: {current_performance.get('position', 'N/A')}\n"
    
    if improvement_goals:
        prompt += f"Improvement Goals: {', '.join(improvement_goals)}\n"
    
    prompt += "\nProvide specific, actionable recommendations to enhance this content."
    
    return prompt