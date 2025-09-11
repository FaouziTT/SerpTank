"""
Validation utilities for services.

This module provides reusable validation functionality for URLs,
email addresses, and other common data types.
"""
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse


class URLValidator:
    """Validator for URLs."""
    
    @staticmethod
    def is_valid_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
        """
        Check if a URL is valid.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes (default: http, https)
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        allowed_schemes = allowed_schemes or ['http', 'https']
        
        try:
            result = urlparse(url)
            return all([
                result.scheme in allowed_schemes,
                result.netloc != '',
                # Basic domain validation
                '.' in result.netloc or result.netloc == 'localhost'
            ])
        except Exception:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a URL for consistent comparison.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url:
            return ""
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url.strip().lower())
            
            # Remove default ports
            netloc = parsed.netloc
            if netloc.endswith(':80') and parsed.scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and parsed.scheme == 'https':
                netloc = netloc[:-4]
            
            # Ensure path ends with / if empty
            path = parsed.path or '/'
            
            # Reconstruct URL
            return f"{parsed.scheme}://{netloc}{path}"
        except Exception:
            return url
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain or None if invalid
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() if parsed.netloc else None
        except Exception:
            return None


class EmailValidator:
    """Validator for email addresses."""
    
    # Simple email regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """
        Check if an email address is valid.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or len(email) > 254:  # Max email length per RFC
            return False
        
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize an email address.
        
        Args:
            email: Email to normalize
            
        Returns:
            Normalized email
        """
        if not email:
            return ""
        
        # Convert to lowercase and strip whitespace
        email = email.strip().lower()
        
        # Handle Gmail plus addressing and dots
        if '@gmail.com' in email:
            local, domain = email.split('@')
            # Remove everything after + in local part
            local = local.split('+')[0]
            # Remove dots from local part
            local = local.replace('.', '')
            email = f"{local}@{domain}"
        
        return email


class TextValidator:
    """Validator for text content."""
    
    @staticmethod
    def contains_profanity(text: str, profanity_list: Optional[List[str]] = None) -> bool:
        """
        Check if text contains profanity.
        
        Args:
            text: Text to check
            profanity_list: Custom list of profane words
            
        Returns:
            True if profanity found, False otherwise
        """
        if not text:
            return False
        
        # Basic profanity list (extend as needed)
        default_profanity = [
            'spam', 'scam', 'xxx', 'porn'
        ]
        
        profanity_list = profanity_list or default_profanity
        text_lower = text.lower()
        
        for word in profanity_list:
            if word in text_lower:
                return True
        
        return False
    
    @staticmethod
    def is_valid_length(
        text: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> bool:
        """
        Check if text length is within bounds.
        
        Args:
            text: Text to check
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            True if valid length, False otherwise
        """
        if not text and min_length:
            return False
        
        text_length = len(text) if text else 0
        
        if min_length is not None and text_length < min_length:
            return False
        
        if max_length is not None and text_length > max_length:
            return False
        
        return True
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove HTML tags from text.
        
        Args:
            text: Text containing HTML
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Simple HTML tag removal
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)


class KeywordValidator:
    """Validator for SEO keywords."""
    
    @staticmethod
    def is_valid_keyword(keyword: str) -> bool:
        """
        Check if a keyword is valid for SEO.
        
        Args:
            keyword: Keyword to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not keyword or not keyword.strip():
            return False
        
        # Check length
        if len(keyword) < 2 or len(keyword) > 100:
            return False
        
        # Check for spammy patterns
        if keyword.count(' ') > 10:  # Too many words
            return False
        
        # Check for special characters abuse
        special_chars = sum(1 for c in keyword if not c.isalnum() and c != ' ')
        if special_chars > len(keyword) * 0.2:  # More than 20% special chars
            return False
        
        return True
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract potential keywords from text.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Simple keyword extraction (can be enhanced with NLP)
        # Remove common words and extract unique words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are',
            'was', 'were', 'been', 'be', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'shall', 'can', 'need'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter and count
        keyword_counts = {}
        for word in words:
            if len(word) > 2 and word not in common_words:
                keyword_counts[word] = keyword_counts.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [kw[0] for kw in sorted_keywords[:max_keywords]]


def validate_api_response(
    response: Dict[str, Any],
    required_fields: List[str],
    field_types: Optional[Dict[str, type]] = None
) -> Dict[str, Any]:
    """
    Validate API response structure.
    
    Args:
        response: API response to validate
        required_fields: List of required fields
        field_types: Optional mapping of field names to expected types
        
    Returns:
        Validation result with 'valid' and 'errors' keys
    """
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")
    
    # Check field types if provided
    if field_types:
        for field, expected_type in field_types.items():
            if field in response and not isinstance(response[field], expected_type):
                actual_type = type(response[field]).__name__
                errors.append(
                    f"Field '{field}' has wrong type. "
                    f"Expected {expected_type.__name__}, got {actual_type}"
                )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }