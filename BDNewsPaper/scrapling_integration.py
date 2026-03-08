"""
Scrapling Integration Module
=============================
Wrapper around the Scrapling library for enhanced web fetching with
native Cloudflare Turnstile bypass support.

Provides:
    - ScraplingFetcherWrapper: Unified interface to Scrapling's three fetcher types
    - ScraplingSessionManager: Thread-safe session reuse per (domain, fetcher_type)
    - fetch(): Takes a Scrapy Request, returns a Scrapy HtmlResponse
    - fetch_for_cloudflare_bypass(): Simplified interface for CF escalation chain

All imports are lazy — module works even if scrapling is not installed.

Scrapling fetcher types:
    - Fetcher: Fast HTTP with TLS fingerprint impersonation via curl_cffi (uses .get())
    - StealthyFetcher: Patchright-based stealth browser with CF Turnstile bypass,
      48+ stealth args, BrowserForge headers (uses .fetch())
    - DynamicFetcher: Patchright browser automation without stealth patches (uses .fetch())
"""

import logging
import threading
from typing import Optional, Tuple
from urllib.parse import urlparse

from scrapy.http import HtmlResponse, Request

logger = logging.getLogger(__name__)

# Lazy import check
SCRAPLING_AVAILABLE = False
_Fetcher = None
_StealthyFetcher = None
_DynamicFetcher = None
_StealthySession = None
_DynamicSession = None

try:
    from scrapling import Fetcher as _Fetcher
    from scrapling import StealthyFetcher as _StealthyFetcher
    from scrapling import DynamicFetcher as _DynamicFetcher
    from scrapling.fetchers import StealthySession as _StealthySession
    from scrapling.fetchers import DynamicSession as _DynamicSession
    SCRAPLING_AVAILABLE = True
except ImportError:
    pass


class ScraplingSessionManager:
    """Thread-safe lazy session manager keyed by (domain, fetcher_type).

    Uses Scrapling's session classes (StealthySession, DynamicSession) to keep
    browsers open across multiple requests to the same domain.
    For the basic Fetcher (HTTP-only), no session is needed.
    """

    def __init__(self, **session_defaults):
        self._sessions = {}
        self._lock = threading.Lock()
        self._session_defaults = session_defaults

    def get_or_create(self, domain: str, fetcher_type: str):
        """Get an existing session or create a new one."""
        key = (domain, fetcher_type)
        with self._lock:
            if key not in self._sessions:
                session = self._create_session(fetcher_type)
                if session is not None:
                    self._sessions[key] = session
                else:
                    return None
            return self._sessions[key]

    def _create_session(self, fetcher_type: str):
        """Create and open a new Scrapling session."""
        if fetcher_type == 'stealthy' and _StealthySession:
            session = _StealthySession(**self._session_defaults)
            session.__enter__()
            return session
        elif fetcher_type == 'dynamic' and _DynamicSession:
            # Filter out StealthyFetcher-only params
            dynamic_defaults = {
                k: v for k, v in self._session_defaults.items()
                if k not in ('hide_canvas', 'block_webrtc', 'solve_cloudflare', 'allow_webgl')
            }
            session = _DynamicSession(**dynamic_defaults)
            session.__enter__()
            return session
        # Basic Fetcher doesn't need sessions
        return None

    def close_all(self):
        """Close all open sessions."""
        with self._lock:
            for session in self._sessions.values():
                try:
                    session.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Error closing scrapling session: {e}")
            self._sessions.clear()


class ScraplingFetcherWrapper:
    """
    Unified interface to Scrapling's three fetcher types.

    Fetcher types:
        - 'basic': Fast HTTP with TLS fingerprint impersonation (Fetcher.get())
        - 'stealthy': Patchright stealth browser with CF Turnstile bypass (StealthyFetcher.fetch())
        - 'dynamic': Patchright browser automation without stealth patches (DynamicFetcher.fetch())
    """

    def __init__(
        self,
        default_fetcher: str = 'stealthy',
        headless: bool = True,
        solve_cloudflare: bool = True,
        timeout: int = 30000,
        hide_canvas: bool = True,
        block_webrtc: bool = True,
        allow_webgl: bool = False,
        disable_images: bool = False,
        use_sessions: bool = True,
    ):
        if not SCRAPLING_AVAILABLE:
            raise RuntimeError("scrapling is not installed. Install with: pip install scrapling")

        self.default_fetcher = default_fetcher
        self.headless = headless
        self.solve_cloudflare = solve_cloudflare
        self.timeout = timeout
        self.hide_canvas = hide_canvas
        self.block_webrtc = block_webrtc
        self.allow_webgl = allow_webgl
        self.disable_images = disable_images
        self.use_sessions = use_sessions

        session_defaults = {'headless': headless}
        if default_fetcher == 'stealthy':
            session_defaults.update({
                'hide_canvas': hide_canvas,
                'block_webrtc': block_webrtc,
            })
        self.session_manager = ScraplingSessionManager(**session_defaults) if use_sessions else None

    def _build_fetch_kwargs(self, url: str, fetcher_type: str, proxy: Optional[str] = None) -> dict:
        """Build kwargs for the Scrapling fetch/get call."""
        kwargs = {'timeout': self.timeout}

        if proxy:
            kwargs['proxy'] = proxy

        if fetcher_type == 'stealthy':
            kwargs['headless'] = self.headless
            kwargs['hide_canvas'] = self.hide_canvas
            kwargs['block_webrtc'] = self.block_webrtc
            kwargs['allow_webgl'] = self.allow_webgl
            kwargs['disable_images'] = self.disable_images
            if self.solve_cloudflare:
                kwargs['solve_cloudflare'] = True
            # google_search=True makes Scrapling navigate via Google first
            # (looks more natural to anti-bot systems)
            kwargs['google_search'] = True
        elif fetcher_type == 'dynamic':
            kwargs['headless'] = self.headless
            kwargs['disable_images'] = self.disable_images
            # DynamicFetcher does NOT support hide_canvas, block_webrtc, solve_cloudflare

        if fetcher_type == 'basic':
            # Fetcher.get() accepts different params
            basic_kwargs = {'stealthy_headers': True, 'follow_redirects': True}
            if proxy:
                basic_kwargs['proxy'] = proxy
            return basic_kwargs

        return kwargs

    def _extract_html(self, response) -> str:
        """Extract HTML content from a Scrapling response object."""
        # Scrapling response: .html_content (str), .body (bytes), .text (text content)
        html_content = getattr(response, 'html_content', None)
        if html_content and isinstance(html_content, str):
            return html_content

        body = getattr(response, 'body', None)
        if body:
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='replace')
            return str(body)

        text = getattr(response, 'text', None)
        if text and isinstance(text, str):
            return text

        return ''

    def _extract_status(self, response) -> int:
        """Extract status code from a Scrapling response object."""
        # Scrapling uses .status (int)
        return getattr(response, 'status', 200)

    def _convert_proxy(self, proxy: Optional[str]) -> Optional[str]:
        """Convert Scrapy proxy URL format to Scrapling's expected format."""
        if not proxy:
            return None
        return proxy

    def _do_fetch(self, url: str, fetcher_type: str, fetch_kwargs: dict, domain: str):
        """Execute the actual fetch via Scrapling."""
        # Try session-based fetch first
        if self.use_sessions and self.session_manager and fetcher_type in ('stealthy', 'dynamic'):
            session = self.session_manager.get_or_create(domain, fetcher_type)
            if session is not None:
                # Session.fetch() accepts per-request overrides
                session_kwargs = {
                    k: v for k, v in fetch_kwargs.items()
                    if k not in ('headless',)  # headless is session-level only
                }
                return session.fetch(url, **session_kwargs)

        # Classmethod-based fetch (opens/closes browser per call)
        if fetcher_type == 'basic':
            return _Fetcher.get(url, **fetch_kwargs)
        elif fetcher_type == 'stealthy':
            return _StealthyFetcher.fetch(url, **fetch_kwargs)
        elif fetcher_type == 'dynamic':
            return _DynamicFetcher.fetch(url, **fetch_kwargs)
        else:
            raise ValueError(f"Unknown fetcher type: {fetcher_type}")

    def fetch(
        self,
        request: Request,
        fetcher_type: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> Optional[HtmlResponse]:
        """
        Fetch a URL using Scrapling and return a Scrapy HtmlResponse.

        Args:
            request: Scrapy Request object
            fetcher_type: One of 'basic', 'stealthy', 'dynamic'. Defaults to self.default_fetcher
            proxy: Optional proxy URL

        Returns:
            HtmlResponse on success, None on failure
        """
        fetcher_type = fetcher_type or self.default_fetcher
        url = request.url
        proxy = self._convert_proxy(proxy or request.meta.get('proxy'))
        domain = urlparse(url).netloc

        try:
            fetch_kwargs = self._build_fetch_kwargs(url, fetcher_type, proxy)
            logger.info(f"Scrapling [{fetcher_type}]: Fetching {url}")

            response = self._do_fetch(url, fetcher_type, fetch_kwargs, domain)

            html = self._extract_html(response)
            status = self._extract_status(response)

            if not html:
                logger.warning(f"Scrapling [{fetcher_type}]: Empty response for {url}")
                return None

            return HtmlResponse(
                url=url,
                status=status,
                body=html.encode('utf-8'),
                encoding='utf-8',
                request=request,
            )

        except Exception as e:
            logger.error(f"Scrapling [{fetcher_type}]: Failed to fetch {url}: {e}")
            return None

    def fetch_for_cloudflare_bypass(
        self,
        url: str,
        proxy: Optional[str] = None,
    ) -> Tuple[Optional[str], int]:
        """
        Simplified fetch interface for the Cloudflare bypass escalation chain.

        Uses StealthyFetcher with solve_cloudflare=True.

        Returns:
            Tuple of (html_content, status_code). html is None on failure.
        """
        proxy = self._convert_proxy(proxy)
        domain = urlparse(url).netloc

        try:
            fetch_kwargs = self._build_fetch_kwargs(url, 'stealthy', proxy)
            # Ensure solve_cloudflare is always on for CF bypass
            fetch_kwargs['solve_cloudflare'] = True

            logger.info(f"Scrapling CF bypass: Fetching {url}")

            response = self._do_fetch(url, 'stealthy', fetch_kwargs, domain)

            html = self._extract_html(response)
            status = self._extract_status(response)

            if html:
                logger.info(f"Scrapling CF bypass: Got {len(html)} chars from {url}")
                return html, status
            else:
                logger.warning(f"Scrapling CF bypass: Empty response for {url}")
                return None, status

        except Exception as e:
            logger.error(f"Scrapling CF bypass: Failed for {url}: {e}")
            return None, 0

    def close(self):
        """Clean up sessions."""
        if self.session_manager:
            self.session_manager.close_all()
