"""Text processing utilities"""

import re
from typing import List
from urllib.parse import urlparse


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text using regex
    
    Args:
        text: Text to extract URLs from
    
    Returns:
        List of unique URLs found
    """
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    return list(set(urls))  # Remove duplicates


def extract_urls_from_multiple_sources(sources: dict) -> List[str]:
    """
    Extract URLs from multiple text sources
    
    Args:
        sources: Dictionary where values might contain text with URLs
    
    Returns:
        List of unique URLs found
    """
    urls = []
    for source_text in sources.values():
        if isinstance(source_text, str):
            urls.extend(extract_urls(source_text))
    return list(set(urls))


def get_domain(url: str) -> str:
    """Get domain from URL"""
    return urlparse(url).netloc


def filter_urls_by_domain(urls: List[str], domain: str) -> List[str]:
    """Filter URLs by specific domain"""
    return [url for url in urls if get_domain(url) == domain]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    return " ".join(text.split())


def extract_json_from_text(text: str) -> dict:
    """
    Extract JSON from text that might contain other content
    
    Args:
        text: Text potentially containing JSON
    
    Returns:
        Parsed JSON dict or empty dict if not found
    """
    import json
    
    # Try to find JSON in curly braces
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return {}
