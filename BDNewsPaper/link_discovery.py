"""
Generic Article Link Discovery
==============================
Universal article link discovery that works across all news sites.

Key Features:
- Pattern-based URL detection (no CSS selectors needed)
- Smart filtering of non-article links
- Multi-strategy link extraction
- Works on any news site structure
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


class ArticleLinkDiscovery:
    """
    Smart article link discovery using URL patterns and heuristics.
    
    Works by analyzing ALL links on a page and filtering based on:
    1. URL patterns common to news articles
    2. Link text heuristics (headlines are typically longer)
    3. Domain-specific patterns
    4. Exclusion of non-article links
    """
    
    # URL patterns that indicate an article
    ARTICLE_URL_PATTERNS = [
        # Numeric ID patterns
        r'/\d{4,}',  # /12345
        r'/news/\d+',  # /news/123
        r'/article/\d+',  # /article/123
        r'/story/\d+',  # /story/123
        r'/post/\d+',  # /post/123
        
        # Date-based patterns
        r'/\d{4}/\d{2}/\d{2}/',  # /2024/12/27/
        r'/\d{4}-\d{2}-\d{2}/',  # /2024-12-27/
        r'/\d{4}/\d{2}/',  # /2024/12/
        
        # Slug patterns (words with hyphens)
        r'/[a-z0-9]+-[a-z0-9]+-[a-z0-9]+',  # /some-article-title
        
        # Common news URL structures
        r'/details/',
        r'/article/',
        r'/news/',
        r'/story/',
        r'/post/',
        r'/read/',
        r'/view/',
        r'/content/',
        r'/archives/',
        r'/\d+/[a-z]',  # /123/article-slug
    ]
    
    # Bengali/Bangla patterns
    BENGALI_PATTERNS = [
        r'/bn/',
        r'/bangla/',
        r'/বাংলা/',
    ]
    
    # URL patterns to EXCLUDE (not articles)
    EXCLUDE_PATTERNS = [
        r'^/tag/',
        r'^/tags/',
        r'^/category/',
        r'^/categories/',
        r'^/author/',
        r'^/authors/',
        r'^/page/',
        r'^/search',
        r'^/login',
        r'^/register',
        r'^/signup',
        r'^/contact',
        r'^/about',
        r'^/privacy',
        r'^/terms',
        r'^/advertis',
        r'^/subscribe',
        r'^/newsletter',
        r'^/rss',
        r'^/feed',
        r'^/api/',
        r'^/admin/',
        r'^/wp-admin',
        r'^/wp-content',
        r'^/wp-includes',
        r'^/assets/',
        r'^/static/',
        r'^/css/',
        r'^/js/',
        r'^/img/',
        r'^/images/',
        r'^/media/',
        r'^/cdn/',
        r'\.pdf$',
        r'\.jpg$',
        r'\.png$',
        r'\.gif$',
        r'\.mp4$',
        r'\.mp3$',
        r'^#',
        r'^javascript:',
        r'^mailto:',
        r'^tel:',
    ]
    
    # File extensions to exclude
    EXCLUDED_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv',
        '.zip', '.rar', '.7z', '.tar', '.gz',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.css', '.js', '.json', '.xml',
    }
    
    def __init__(self, base_domain: str = ""):
        self.base_domain = base_domain
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.article_regexes = [re.compile(p, re.IGNORECASE) for p in self.ARTICLE_URL_PATTERNS]
        self.exclude_regexes = [re.compile(p, re.IGNORECASE) for p in self.EXCLUDE_PATTERNS]
    
    def discover_links(self, response, min_links: int = 5) -> List[Dict]:
        """
        Discover article links from a Scrapy response.
        
        Args:
            response: Scrapy Response object
            min_links: Minimum expected article links (for validation)
            
        Returns:
            List of dicts with 'url', 'text', 'score' keys
        """
        all_links = self._extract_all_links(response)
        scored_links = self._score_links(all_links, response.url)
        
        # Filter and sort by score
        article_links = [
            link for link in scored_links 
            if link['score'] >= 2 and link['is_article']
        ]
        
        # Sort by score (highest first)
        article_links.sort(key=lambda x: x['score'], reverse=True)
        
        logger.debug(f"Discovered {len(article_links)} article links from {len(all_links)} total")
        
        return article_links
    
    def _extract_all_links(self, response) -> List[Dict]:
        """Extract all links with their text from the page."""
        links = []
        seen_urls = set()
        
        # Strategy 1: Standard anchor tags
        for a_tag in response.css('a[href]'):
            href = a_tag.css('::attr(href)').get()
            if not href:
                continue
                
            # Get link text
            text = a_tag.css('::text').get() or ''
            # Also try to get text from nested elements
            if not text.strip():
                text = ' '.join(a_tag.css('*::text').getall())
            text = ' '.join(text.split())  # Normalize whitespace
            
            # Resolve relative URLs
            full_url = urljoin(response.url, href)
            
            # Skip duplicates
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            links.append({
                'url': full_url,
                'href': href,
                'text': text,
            })
        
        return links
    
    def _score_links(self, links: List[Dict], page_url: str) -> List[Dict]:
        """Score links based on article likelihood."""
        page_domain = urlparse(page_url).netloc
        
        for link in links:
            score = 0
            is_article = True
            reasons = []
            
            url = link['url']
            href = link.get('href', '')
            text = link.get('text', '')
            
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Check exclusion patterns first
            for regex in self.exclude_regexes:
                if regex.search(path):
                    is_article = False
                    reasons.append('excluded_pattern')
                    break
            
            # Check file extension
            for ext in self.EXCLUDED_EXTENSIONS:
                if path.endswith(ext):
                    is_article = False
                    reasons.append('excluded_extension')
                    break
            
            if not is_article:
                link['score'] = 0
                link['is_article'] = False
                link['reasons'] = reasons
                continue
            
            # Same domain check (+1)
            if parsed.netloc == page_domain or not parsed.netloc:
                score += 1
                reasons.append('same_domain')
            
            # Article URL patterns (+2 each)
            for regex in self.article_regexes:
                if regex.search(path):
                    score += 2
                    reasons.append('article_pattern')
                    break
            
            # Long URL path suggests article (+1)
            if len(path) > 20:
                score += 1
                reasons.append('long_path')
            
            # URL has slug-like structure (+2)
            if re.search(r'/[a-z0-9]+-[a-z0-9]+-[a-z0-9]+', path):
                score += 2
                reasons.append('slug_structure')
            
            # Has numeric ID in URL (+1)
            if re.search(r'/\d{4,}', path):
                score += 1
                reasons.append('numeric_id')
            
            # Link text is headline-like (+2)
            if text and len(text) > 20 and len(text) < 200:
                # Headline-like: starts with capital, no excessive punctuation
                if text[0].isupper() or ord(text[0]) > 127:  # Allow Bengali
                    score += 2
                    reasons.append('headline_text')
            
            # Penalize very short paths (-1)
            if len(path) < 5:
                score -= 1
                reasons.append('short_path')
            
            # Penalize homepage links (-2)
            if path in ['/', '', '/index.html', '/home']:
                score -= 2
                reasons.append('homepage')
            
            link['score'] = max(0, score)
            link['is_article'] = score >= 2
            link['reasons'] = reasons
        
        return links
    
    def get_article_urls(self, response, limit: int = 50) -> List[str]:
        """
        Simple method to get article URLs from a page.
        
        Args:
            response: Scrapy Response object
            limit: Maximum number of URLs to return
            
        Returns:
            List of article URLs
        """
        links = self.discover_links(response)
        return [link['url'] for link in links[:limit]]


def discover_article_links(response, limit: int = 50) -> List[str]:
    """
    Convenience function for quick article link discovery.
    
    Usage in spider:
        from BDNewsPaper.link_discovery import discover_article_links
        
        def parse(self, response):
            article_urls = discover_article_links(response)
            for url in article_urls:
                yield scrapy.Request(url, callback=self.parse_article)
    """
    discoverer = ArticleLinkDiscovery()
    return discoverer.get_article_urls(response, limit)


def score_url_as_article(url: str) -> int:
    """
    Score a single URL for article likelihood.
    
    Args:
        url: URL to score
        
    Returns:
        Score (0-10, higher = more likely article)
    """
    discoverer = ArticleLinkDiscovery()
    links = discoverer._score_links([{'url': url, 'href': url, 'text': ''}], url)
    return links[0]['score'] if links else 0
