"""
Honeypot Detection Middleware
=============================
Detects and avoids anti-bot honeypot traps.

Features:
    - Detects invisible links (CSS display:none, visibility:hidden)
    - Blocks suspicious URL patterns
    - Tracks trap URLs in memory blocklist
    - Limits links per page to avoid trap pages

Settings:
    - HONEYPOT_DETECTION_ENABLED: Enable/disable (default: True)
    - HONEYPOT_MAX_LINKS_PER_PAGE: Max links before suspecting trap (default: 500)
    - HONEYPOT_SUSPICIOUS_PATTERNS: URL patterns to avoid
"""

import re
import logging
from collections import defaultdict
from typing import Set, List, Optional
from urllib.parse import urlparse

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import IgnoreRequest, NotConfigured

logger = logging.getLogger(__name__)


class HoneypotDetectionMiddleware:
    """
    Middleware to detect and avoid honeypot traps.
    
    Honeypots are fake links designed to catch bots:
    - Invisible links (CSS hidden)
    - Links with suspicious patterns
    - Pages with excessive links (trap pages)
    """
    
    # Suspicious URL patterns that often indicate traps
    DEFAULT_SUSPICIOUS_PATTERNS = [
        r'/trap/',
        r'/honeypot/',
        r'/click-here/',
        r'/bot-trap/',
        r'/verify-human/',
        r'\?token=[a-f0-9]{32,}',  # Long random tokens
        r'/wp-admin/',  # WordPress admin
        r'/xmlrpc\.php',
        r'/feed/$',  # RSS feeds in most cases
    ]
    
    def __init__(
        self,
        enabled: bool = True,
        max_links_per_page: int = 500,
        suspicious_patterns: List[str] = None,
    ):
        self.enabled = enabled
        self.max_links_per_page = max_links_per_page
        
        # Compile patterns
        patterns = suspicious_patterns or self.DEFAULT_SUSPICIOUS_PATTERNS
        self.suspicious_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Track blocked URLs and trap pages
        self.blocked_urls: Set[str] = set()
        self.trap_pages: Set[str] = set()
        
        self.stats = {
            'invisible_links_blocked': 0,
            'suspicious_patterns_blocked': 0,
            'trap_pages_detected': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('HONEYPOT_DETECTION_ENABLED', True)
        if not enabled:
            raise NotConfigured("Honeypot detection disabled")
        
        middleware = cls(
            enabled=True,
            max_links_per_page=crawler.settings.getint('HONEYPOT_MAX_LINKS_PER_PAGE', 500),
            suspicious_patterns=crawler.settings.getlist('HONEYPOT_SUSPICIOUS_PATTERNS', None),
        )
        
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Filter out honeypot requests."""
        if not self.enabled:
            return None
        
        url = request.url
        
        # Check if URL is in blocklist
        if url in self.blocked_urls:
            spider.logger.debug(f"Blocked known trap URL: {url}")
            raise IgnoreRequest(f"Honeypot URL blocked: {url}")
        
        # Check source page
        referer = request.headers.get(b'Referer', b'').decode('utf-8', errors='ignore')
        if referer in self.trap_pages:
            spider.logger.debug(f"Blocking request from trap page: {referer}")
            raise IgnoreRequest(f"Request from trap page blocked")
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.search(url):
                self.stats['suspicious_patterns_blocked'] += 1
                self.blocked_urls.add(url)
                spider.logger.warning(f"Honeypot: Suspicious pattern in URL: {url}")
                raise IgnoreRequest(f"Suspicious URL pattern blocked: {url}")
        
        # Check meta for honeypot flags
        if request.meta.get('is_honeypot'):
            self.stats['invisible_links_blocked'] += 1
            self.blocked_urls.add(url)
            spider.logger.warning(f"Honeypot: Invisible link blocked: {url}")
            raise IgnoreRequest(f"Invisible link blocked: {url}")
        
        return None
    
    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Analyze response for trap page characteristics."""
        if not self.enabled:
            return response
        
        # Count links in response
        try:
            link_count = len(response.css('a::attr(href)').getall())
            
            if link_count > self.max_links_per_page:
                self.stats['trap_pages_detected'] += 1
                self.trap_pages.add(response.url)
                spider.logger.warning(
                    f"Honeypot: Trap page detected ({link_count} links): {response.url}"
                )
                # Don't block the response, but flag it
                request.meta['is_trap_page'] = True
                
        except Exception:
            pass
        
        return response
    
    def spider_closed(self, spider, reason):
        """Log honeypot statistics."""
        total_blocked = (
            self.stats['invisible_links_blocked'] + 
            self.stats['suspicious_patterns_blocked']
        )
        
        if total_blocked > 0 or self.stats['trap_pages_detected'] > 0:
            spider.logger.info(
                f"Honeypot Detection Stats: "
                f"InvisibleBlocked={self.stats['invisible_links_blocked']}, "
                f"SuspiciousBlocked={self.stats['suspicious_patterns_blocked']}, "
                f"TrapPagesDetected={self.stats['trap_pages_detected']}"
            )


def is_invisible_link(element) -> bool:
    """
    Check if a link element is invisible (CSS hidden).
    
    Use this in spider parse methods:
        from BDNewsPaper.honeypot import is_invisible_link
        
        for link in response.css('a'):
            if not is_invisible_link(link):
                yield response.follow(link, ...)
    """
    try:
        style = element.attrib.get('style', '').lower()
        
        # Check inline styles
        if 'display:none' in style or 'display: none' in style:
            return True
        if 'visibility:hidden' in style or 'visibility: hidden' in style:
            return True
        if 'opacity:0' in style or 'opacity: 0' in style:
            return True
        
        # Check for tiny dimensions
        if 'width:0' in style or 'height:0' in style:
            return True
        if 'font-size:0' in style:
            return True
        
        # Check class for common hiding classes
        classes = element.attrib.get('class', '').lower()
        hidden_classes = ['hidden', 'hide', 'd-none', 'invisible', 'sr-only', 'visually-hidden']
        if any(hc in classes for hc in hidden_classes):
            return True
            
    except Exception:
        pass
    
    return False
