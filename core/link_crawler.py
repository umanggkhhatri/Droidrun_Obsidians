"""HTTP-based link crawler for extracting context from URLs"""

import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from utils import get_logger


logger = get_logger(__name__)


class LinkCrawler:
    """
    HTTP-based crawler for extracting content from URLs.
    
    Crawls the main page and all first-level internal links.
    Uses requests + BeautifulSoup (no DroidAgent).
    """

    def __init__(
        self,
        max_links_per_page: int = 10,
        timeout: int = 15,
    ):
        """
        Initialize HTTP link crawler
        
        Args:
            max_links_per_page: Maximum internal links to follow per page (default: 10)
            timeout: Request timeout in seconds (default: 15)
        """
        self.max_links_per_page = max_links_per_page
        self.timeout = timeout
        self.visited_urls: Set[str] = set()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def crawl_url(self, url: str) -> str:
        """
        Crawl a URL and its first-level internal links.
        
        Args:
            url: The main URL to crawl
        
        Returns:
            Combined text content from main page and all crawled links
        """
        logger.info(f"🔗 Starting HTTP crawl for: {url}")
        self.visited_urls.clear()
        
        all_content = []
        
        # Crawl the main page
        main_content, internal_links = self._fetch_page(url)
        
        if main_content:
            all_content.append(f"=== MAIN PAGE: {url} ===\n{main_content}")
            self.visited_urls.add(url)
            logger.info(f"✅ Crawled main page, found {len(internal_links)} internal links")
        else:
            logger.warning(f"❌ Failed to crawl main page: {url}")
            return ""
        
        # Crawl first-level internal links
        links_to_crawl = internal_links[:self.max_links_per_page]
        
        for link in links_to_crawl:
            if link not in self.visited_urls:
                self.visited_urls.add(link)
                page_content, _ = self._fetch_page(link)
                
                if page_content:
                    all_content.append(f"\n=== LINKED PAGE: {link} ===\n{page_content}")
                    logger.info(f"✅ Crawled: {link}")
                else:
                    logger.warning(f"⚠️ Could not crawl: {link}")
        
        combined = "\n\n".join(all_content)
        logger.info(f"🔗 Crawl complete: {len(self.visited_urls)} pages, {len(combined)} chars total")
        
        return combined

    def _fetch_page(self, url: str) -> tuple[Optional[str], List[str]]:
        """
        Fetch a single page and extract content + internal links.
        
        Args:
            url: URL to fetch
        
        Returns:
            Tuple of (extracted_text, list_of_internal_links)
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract text content
            text_content = self._extract_text(soup, url)
            
            # Extract internal links
            internal_links = self._extract_internal_links(soup, url)
            
            return text_content, internal_links
        
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {str(e)}")
            return None, []
        except Exception as e:
            logger.error(f"Error parsing {url}: {str(e)}")
            return None, []

    def _extract_text(self, soup: BeautifulSoup, url: str) -> str:
        """
        Extract meaningful text content from parsed HTML.
        
        Args:
            soup: BeautifulSoup object
            url: Source URL for context
        
        Returns:
            Extracted text content
        """
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
            element.decompose()
        
        content_parts = []
        
        # Extract title
        title = soup.find("title")
        if title:
            content_parts.append(f"Title: {title.get_text(strip=True)}")
        
        # Extract meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content_parts.append(f"Description: {meta_desc['content']}")
        
        # Extract headings
        headings = []
        for tag in ["h1", "h2", "h3"]:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text:
                    headings.append(f"{tag.upper()}: {text}")
        if headings:
            content_parts.append("Headings:\n" + "\n".join(headings))
        
        # Extract main content from article, main, or body
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        
        if main_content:
            # Get all paragraphs
            paragraphs = []
            for p in main_content.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Skip very short paragraphs
                    paragraphs.append(text)
            
            if paragraphs:
                content_parts.append("Content:\n" + "\n\n".join(paragraphs))
            
            # Get list items
            list_items = []
            for li in main_content.find_all("li"):
                text = li.get_text(strip=True)
                if text and len(text) > 10:
                    list_items.append(f"• {text}")
            
            if list_items:
                content_parts.append("List Items:\n" + "\n".join(list_items[:20]))  # Limit list items
        
        return "\n\n".join(content_parts)

    def _extract_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract internal links from the page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
        
        Returns:
            List of absolute internal URLs
        """
        base_domain = urlparse(base_url).netloc
        internal_links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # Skip anchors, javascript, mailto
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Parse and check domain
            parsed = urlparse(full_url)
            
            # Only include HTTP(S) links from same domain
            if parsed.scheme in ("http", "https") and parsed.netloc == base_domain:
                # Normalize URL (remove fragment)
                normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    normalized += f"?{parsed.query}"
                
                if normalized not in internal_links and normalized != base_url:
                    internal_links.append(normalized)
        
        return internal_links

    def reset(self) -> None:
        """Reset crawler state"""
        self.visited_urls.clear()
        logger.info("Crawler state reset")


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from text content.
    
    Args:
        text: Text that may contain URLs
    
    Returns:
        List of extracted URLs
    """
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    
    # Clean up URLs (remove trailing punctuation)
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:!?)")
        if url and len(url) > 10:
            cleaned.append(url)
    
    return list(set(cleaned))  # Remove duplicates
