"""Text processing utilities"""

import re
from typing import List
import json


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


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_json_from_text(text: str) -> dict:
    """
    Extract JSON from text that might contain other content
    
    Args:
        text: Text potentially containing JSON
    
    Returns:
        Parsed JSON dict or empty dict if not found
    """
    # Try to find JSON in curly braces
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return {}
