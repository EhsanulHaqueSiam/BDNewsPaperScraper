"""
CAPTCHA & Anti-Bot Bypass Module
=================================
Multi-provider CAPTCHA solving and commercial anti-bot bypass.

Supports:
    - reCAPTCHA v2 (checkbox + invisible)
    - reCAPTCHA v3 (score-based)
    - hCaptcha
    - Cloudflare Turnstile
    - Akamai Bot Manager (_abck cookie generation)
    - DataDome
    - PerimeterX/HUMAN
    - Imperva/Incapsula

CAPTCHA Solving Providers:
    - 2Captcha / RuCaptcha
    - CapSolver
    - AntiCaptcha
    - CapMonster

Settings:
    CAPTCHA_ENABLED = False
    CAPTCHA_PROVIDER = 'capsolver'  # '2captcha', 'capsolver', 'anticaptcha', 'capmonster'
    CAPTCHA_API_KEY = ''  # Via environment: CAPTCHA_API_KEY
    AKAMAI_BYPASS_ENABLED = False
    DATADOME_BYPASS_ENABLED = False
    PERIMETERX_BYPASS_ENABLED = False
    INCAPSULA_BYPASS_ENABLED = False
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlencode

from scrapy import signals
from scrapy.http import HtmlResponse, Request, Response
from scrapy.exceptions import NotConfigured

from BDNewsPaper.enums import ProtectionType

logger = logging.getLogger(__name__)


# =============================================================================
# CAPTCHA SOLVER - MULTI-PROVIDER
# =============================================================================

class CaptchaSolver:
    """
    Base captcha solver with multi-provider support.

    Communicates with external CAPTCHA-solving services via their HTTP APIs
    using only ``urllib.request`` (no extra dependencies).

    Supported providers:
        - ``2captcha``   (https://2captcha.com)
        - ``capsolver``  (https://capsolver.com)
        - ``anticaptcha`` (https://anti-captcha.com)
        - ``capmonster`` (https://capmonster.cloud)
    """

    # Provider base URLs
    PROVIDER_URLS: Dict[str, Dict[str, str]] = {
        '2captcha': {
            'submit': 'https://2captcha.com/in.php',
            'result': 'https://2captcha.com/res.php',
        },
        'capsolver': {
            'create': 'https://api.capsolver.com/createTask',
            'result': 'https://api.capsolver.com/getTaskResult',
        },
        'anticaptcha': {
            'create': 'https://api.anti-captcha.com/createTask',
            'result': 'https://api.anti-captcha.com/getTaskResult',
        },
        'capmonster': {
            'create': 'https://api.capmonster.cloud/createTask',
            'result': 'https://api.capmonster.cloud/getTaskResult',
        },
    }

    def __init__(
        self,
        provider: str = 'capsolver',
        api_key: str = '',
        poll_interval: float = 3.0,
        max_timeout: int = 120,
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv('CAPTCHA_API_KEY', '')
        self.poll_interval = poll_interval
        self.max_timeout = max_timeout

        if self.provider not in self.PROVIDER_URLS:
            raise ValueError(
                f"Unsupported CAPTCHA provider '{self.provider}'. "
                f"Choose from: {', '.join(self.PROVIDER_URLS)}"
            )

        if not self.api_key:
            logger.warning("CaptchaSolver initialised without an API key")

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    def _solve_with_retry(self, solve_func, *args, max_retries=2, **kwargs):
        """Retry failed CAPTCHA solves with exponential backoff."""
        for attempt in range(max_retries + 1):
            result = solve_func(*args, **kwargs)
            if result:
                return result
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                logger.info(f"Retrying CAPTCHA solve (attempt {attempt + 2}/{max_retries + 1})")
        return None

    # ------------------------------------------------------------------
    # Public solving methods
    # ------------------------------------------------------------------

    def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Solve reCAPTCHA v2, return g-recaptcha-response token."""
        return self._solve_with_retry(
            self._solve_recaptcha_v2_once,
            site_key, page_url, invisible, timeout,
        )

    def _solve_recaptcha_v2_once(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Single attempt to solve reCAPTCHA v2."""
        timeout = timeout or self.max_timeout

        if self.provider == '2captcha':
            return self._solve_2captcha(
                method='userrecaptcha',
                extra_params={
                    'googlekey': site_key,
                    'pageurl': page_url,
                    'invisible': int(invisible),
                },
                timeout=timeout,
            )

        # CapSolver / AntiCaptcha / CapMonster share the same task API
        task_type = 'RecaptchaV2TaskProxyless'
        if self.provider == 'capsolver':
            task_type = 'ReCaptchaV2TaskProxyLess'

        return self._solve_task_api(
            task={
                'type': task_type,
                'websiteURL': page_url,
                'websiteKey': site_key,
                'isInvisible': invisible,
            },
            timeout=timeout,
        )

    def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = 'verify',
        min_score: float = 0.7,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Solve reCAPTCHA v3, return token with target score."""
        return self._solve_with_retry(
            self._solve_recaptcha_v3_once,
            site_key, page_url, action, min_score, timeout,
        )

    def _solve_recaptcha_v3_once(
        self,
        site_key: str,
        page_url: str,
        action: str = 'verify',
        min_score: float = 0.7,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Single attempt to solve reCAPTCHA v3."""
        timeout = timeout or self.max_timeout

        if self.provider == '2captcha':
            return self._solve_2captcha(
                method='userrecaptcha',
                extra_params={
                    'googlekey': site_key,
                    'pageurl': page_url,
                    'version': 'v3',
                    'action': action,
                    'min_score': str(min_score),
                },
                timeout=timeout,
            )

        task_type = 'RecaptchaV3TaskProxyless'
        if self.provider == 'capsolver':
            task_type = 'ReCaptchaV3TaskProxyLess'

        return self._solve_task_api(
            task={
                'type': task_type,
                'websiteURL': page_url,
                'websiteKey': site_key,
                'pageAction': action,
                'minScore': min_score,
            },
            timeout=timeout,
        )

    def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Solve hCaptcha, return response token."""
        return self._solve_with_retry(
            self._solve_hcaptcha_once,
            site_key, page_url, timeout,
        )

    def _solve_hcaptcha_once(
        self,
        site_key: str,
        page_url: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Single attempt to solve hCaptcha."""
        timeout = timeout or self.max_timeout

        if self.provider == '2captcha':
            return self._solve_2captcha(
                method='hcaptcha',
                extra_params={
                    'sitekey': site_key,
                    'pageurl': page_url,
                },
                timeout=timeout,
            )

        task_type = 'HCaptchaTaskProxyless'
        if self.provider == 'capsolver':
            task_type = 'HCaptchaTaskProxyLess'

        return self._solve_task_api(
            task={
                'type': task_type,
                'websiteURL': page_url,
                'websiteKey': site_key,
            },
            timeout=timeout,
        )

    def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Solve Cloudflare Turnstile, return cf-turnstile-response."""
        return self._solve_with_retry(
            self._solve_turnstile_once,
            site_key, page_url, timeout,
        )

    def _solve_turnstile_once(
        self,
        site_key: str,
        page_url: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Single attempt to solve Cloudflare Turnstile."""
        timeout = timeout or self.max_timeout

        if self.provider == '2captcha':
            return self._solve_2captcha(
                method='turnstile',
                extra_params={
                    'sitekey': site_key,
                    'pageurl': page_url,
                },
                timeout=timeout,
            )

        task_type = 'TurnstileTaskProxyless'
        if self.provider == 'capsolver':
            task_type = 'AntiTurnstileTaskProxyLess'

        return self._solve_task_api(
            task={
                'type': task_type,
                'websiteURL': page_url,
                'websiteKey': site_key,
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # 2Captcha submit + poll flow
    # ------------------------------------------------------------------

    def _solve_2captcha(
        self,
        method: str,
        extra_params: Dict[str, Any],
        timeout: int,
    ) -> Optional[str]:
        """Submit to 2Captcha/RuCaptcha and poll for result."""
        urls = self.PROVIDER_URLS['2captcha']

        # Step 1: Submit
        params = {
            'key': self.api_key,
            'method': method,
            'json': '1',
            **extra_params,
        }
        submit_url = f"{urls['submit']}?{urlencode(params)}"

        try:
            logger.debug("2Captcha: submitting task (method=%s)", method)
            resp = self._http_get(submit_url, timeout=30)
            data = json.loads(resp)
        except Exception as exc:
            logger.error("2Captcha submit failed: %s", exc)
            return None

        if data.get('status') != 1:
            logger.error("2Captcha submit error: %s", data.get('request'))
            return None

        task_id = data['request']
        logger.info("2Captcha: task created id=%s", task_id)

        # Step 2: Poll
        result_params = {
            'key': self.api_key,
            'action': 'get',
            'id': task_id,
            'json': '1',
        }
        result_url = f"{urls['result']}?{urlencode(result_params)}"

        return self._poll_2captcha(result_url, timeout)

    def _poll_2captcha(self, result_url: str, timeout: int) -> Optional[str]:
        """Poll 2Captcha result endpoint until ready or timeout."""
        deadline = time.monotonic() + timeout
        # Initial wait before first poll
        time.sleep(min(5, self.poll_interval))

        while time.monotonic() < deadline:
            try:
                resp = self._http_get(result_url, timeout=15)
                data = json.loads(resp)
            except Exception as exc:
                logger.warning("2Captcha poll error: %s", exc)
                time.sleep(self.poll_interval)
                continue

            if data.get('status') == 1:
                token = data.get('request', '')
                logger.info("2Captcha: solved successfully")
                return token

            error = data.get('request', '')
            if error == 'CAPCHA_NOT_READY':
                logger.debug("2Captcha: not ready yet, polling...")
                time.sleep(self.poll_interval)
                continue

            # Real error
            logger.error("2Captcha result error: %s", error)
            return None

        logger.error("2Captcha: timed out after %ds", timeout)
        return None

    # ------------------------------------------------------------------
    # Task-based API flow (CapSolver / AntiCaptcha / CapMonster)
    # ------------------------------------------------------------------

    def _solve_task_api(
        self,
        task: Dict[str, Any],
        timeout: int,
    ) -> Optional[str]:
        """Create task and poll via JSON task API (CapSolver/AntiCaptcha/CapMonster)."""
        urls = self.PROVIDER_URLS[self.provider]

        # Step 1: Create task
        create_payload = {
            'clientKey': self.api_key,
            'task': task,
        }

        try:
            logger.debug("%s: creating task type=%s", self.provider, task.get('type'))
            resp = self._http_post_json(urls['create'], create_payload, timeout=30)
            data = json.loads(resp)
        except Exception as exc:
            logger.error("%s createTask failed: %s", self.provider, exc)
            return None

        error_id = data.get('errorId', 0)
        if error_id != 0:
            logger.error(
                "%s createTask error %s: %s",
                self.provider,
                data.get('errorCode'),
                data.get('errorDescription'),
            )
            return None

        task_id = data.get('taskId')
        if not task_id:
            logger.error("%s: no taskId in response", self.provider)
            return None

        logger.info("%s: task created id=%s", self.provider, task_id)

        # Step 2: Poll
        return self._poll_task_api(urls['result'], task_id, timeout)

    def _poll_task_api(
        self,
        result_url: str,
        task_id: str,
        timeout: int,
    ) -> Optional[str]:
        """Poll task-based API until ready or timeout."""
        deadline = time.monotonic() + timeout
        time.sleep(min(5, self.poll_interval))

        while time.monotonic() < deadline:
            payload = {
                'clientKey': self.api_key,
                'taskId': task_id,
            }

            try:
                resp = self._http_post_json(result_url, payload, timeout=15)
                data = json.loads(resp)
            except Exception as exc:
                logger.warning("%s poll error: %s", self.provider, exc)
                time.sleep(self.poll_interval)
                continue

            error_id = data.get('errorId', 0)
            if error_id != 0:
                logger.error(
                    "%s result error %s: %s",
                    self.provider,
                    data.get('errorCode'),
                    data.get('errorDescription'),
                )
                return None

            status = data.get('status', '')
            if status == 'ready':
                solution = data.get('solution', {})
                token = (
                    solution.get('gRecaptchaResponse')
                    or solution.get('token')
                    or solution.get('text')
                    or ''
                )
                logger.info("%s: solved successfully", self.provider)
                return token if token else None

            if status == 'processing':
                logger.debug("%s: still processing...", self.provider)
                time.sleep(self.poll_interval)
                continue

            # Unknown status
            logger.warning("%s: unexpected status '%s'", self.provider, status)
            time.sleep(self.poll_interval)

        logger.error("%s: timed out after %ds", self.provider, timeout)
        return None

    # ------------------------------------------------------------------
    # HTTP helpers (urllib only - no extra deps)
    # ------------------------------------------------------------------

    @staticmethod
    def _http_get(url: str, timeout: int = 30) -> str:
        """Perform a simple HTTP GET and return response body as string."""
        req = urllib.request.Request(url, method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8')

    @staticmethod
    def _http_post_json(url: str, payload: Dict, timeout: int = 30) -> str:
        """Perform an HTTP POST with JSON body and return response body."""
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8')


# =============================================================================
# CAPTCHA DETECTION HELPERS
# =============================================================================

# Patterns that indicate a CAPTCHA challenge page
RECAPTCHA_PATTERNS = [
    re.compile(r'class=["\']g-recaptcha["\']', re.I),
    re.compile(r'data-sitekey=["\']([^"\']+)["\']', re.I),
    re.compile(r'google\.com/recaptcha/api', re.I),
    re.compile(r'grecaptcha\.execute', re.I),
]

HCAPTCHA_PATTERNS = [
    re.compile(r'class=["\']h-captcha["\']', re.I),
    re.compile(r'hcaptcha\.com/1/api\.js', re.I),
    re.compile(r'data-sitekey=["\']([^"\']+)["\']', re.I),
]

TURNSTILE_PATTERNS = [
    re.compile(r'cf-turnstile', re.I),
    re.compile(r'challenges\.cloudflare\.com/turnstile', re.I),
]


def detect_captcha_type(html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect CAPTCHA type and extract site key from HTML.

    Returns:
        Tuple of (captcha_type, site_key) where captcha_type is one of
        'recaptcha_v2', 'recaptcha_v3', 'hcaptcha', 'turnstile', or None.
    """
    if not html:
        return None, None

    text = html[:10000]  # Only scan first 10KB

    # reCAPTCHA v3 (must check before v2 since v3 pages may also have the anchor)
    if re.search(r'grecaptcha\.execute', text, re.I):
        site_key = _extract_site_key(text)
        return 'recaptcha_v3', site_key

    # reCAPTCHA v2
    for pat in RECAPTCHA_PATTERNS:
        if pat.search(text):
            site_key = _extract_site_key(text)
            return 'recaptcha_v2', site_key

    # hCaptcha
    for pat in HCAPTCHA_PATTERNS:
        if pat.search(text):
            site_key = _extract_site_key(text)
            return 'hcaptcha', site_key

    # Turnstile
    for pat in TURNSTILE_PATTERNS:
        if pat.search(text):
            site_key = _extract_site_key(text)
            return 'turnstile', site_key

    return None, None


def _extract_site_key(html: str) -> Optional[str]:
    """Extract data-sitekey value from HTML."""
    match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html, re.I)
    if match:
        return match.group(1)

    # CapSolver-style render key
    match = re.search(r'grecaptcha\.render\s*\(\s*[^,]+,\s*\{\s*["\']sitekey["\']\s*:\s*["\']([^"\']+)["\']', html, re.I)
    if match:
        return match.group(1)

    # Turnstile key
    match = re.search(r'turnstile\.render\s*\(\s*[^,]+,\s*\{\s*sitekey\s*:\s*["\']([^"\']+)["\']', html, re.I)
    if match:
        return match.group(1)

    return None


# =============================================================================
# AKAMAI BOT MANAGER BYPASS
# =============================================================================

class AkamaiBypass:
    """
    Akamai Bot Manager sensor data bypass.

    Detects Akamai protection by looking for characteristic cookies
    (``_abck``, ``bm_sz``, ``ak_bmsc``) and headers, then obtains valid
    cookies via browser automation (Playwright).
    """

    AKAMAI_INDICATORS = [
        '_abck',     # Akamai bot management cookie
        'bm_sz',     # Akamai size cookie
        'ak_bmsc',   # Akamai behavioral cookie
    ]

    AKAMAI_HEADER_INDICATORS = [
        'x-akamai-session',
        'akamai-grn',
    ]

    AKAMAI_SCRIPT_PATTERNS = [
        re.compile(r'/akam/[\d]+/[\w]+', re.I),
        re.compile(r'_abck', re.I),
        re.compile(r'bmak\.js', re.I),
    ]

    def __init__(self, browser_timeout: int = 30):
        self.browser_timeout = browser_timeout

    def detect(self, response: Response) -> bool:
        """Detect Akamai protection from response cookies/headers."""
        # Check cookies
        cookies = self._get_cookies(response)
        for indicator in self.AKAMAI_INDICATORS:
            if indicator in cookies:
                logger.debug("Akamai detected via cookie: %s", indicator)
                return True

        # Check response headers
        for header_name in self.AKAMAI_HEADER_INDICATORS:
            if response.headers.get(header_name):
                logger.debug("Akamai detected via header: %s", header_name)
                return True

        # Check response body for Akamai script includes
        try:
            text = response.text[:10000]
        except Exception:
            return False

        for pattern in self.AKAMAI_SCRIPT_PATTERNS:
            if pattern.search(text):
                logger.debug("Akamai detected via script pattern")
                return True

        return False

    def generate_sensor_data(self, page_url: str) -> Optional[str]:
        """
        Generate Akamai sensor data using browser automation.

        Uses Playwright to load the page, execute the Akamai JS, and
        capture the resulting ``_abck`` cookie value. Returns the cookie
        value, or None on failure.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed; cannot generate Akamai sensor data")
            return None

        abck_value = None
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ],
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/136.0.0.0 Safari/537.36'
                    ),
                )

                # Inject stealth patches
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                page = context.new_page()
                page.goto(page_url, wait_until='networkidle', timeout=self.browser_timeout * 1000)

                # Wait for Akamai script to generate _abck cookie
                page.wait_for_timeout(3000)

                cookies = context.cookies()
                for cookie in cookies:
                    if cookie['name'] == '_abck':
                        abck_value = cookie['value']
                        break

                browser.close()

        except Exception as exc:
            logger.error("Akamai sensor generation failed: %s", exc)

        return abck_value

    def get_valid_cookies(self, page_url: str) -> Dict[str, str]:
        """
        Get valid Akamai cookies via a full browser session.

        Returns a dictionary of all Akamai-related cookies extracted from
        a Playwright session after the Akamai JS has executed.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed; cannot get Akamai cookies")
            return {}

        result: Dict[str, str] = {}
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ],
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/136.0.0.0 Safari/537.36'
                    ),
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                page = context.new_page()
                page.goto(page_url, wait_until='networkidle', timeout=self.browser_timeout * 1000)

                # Allow Akamai JS to execute fully
                page.wait_for_timeout(5000)

                cookies = context.cookies()
                akamai_names = set(self.AKAMAI_INDICATORS)
                for cookie in cookies:
                    if cookie['name'] in akamai_names:
                        result[cookie['name']] = cookie['value']

                browser.close()

        except Exception as exc:
            logger.error("Akamai cookie extraction failed: %s", exc)

        if result:
            logger.info("Akamai: extracted %d cookies from %s", len(result), page_url)
        else:
            logger.warning("Akamai: no cookies extracted from %s", page_url)

        return result

    @staticmethod
    def _get_cookies(response: Response) -> Dict[str, str]:
        """Extract cookies from a Scrapy response via Set-Cookie headers."""
        cookies: Dict[str, str] = {}
        for header_value in response.headers.getlist('Set-Cookie'):
            decoded = header_value.decode('utf-8', errors='replace')
            if '=' in decoded:
                name, _, rest = decoded.partition('=')
                value = rest.split(';', 1)[0]
                cookies[name.strip()] = value.strip()
        return cookies


# =============================================================================
# DATADOME BYPASS
# =============================================================================

class DataDomeBypass:
    """
    DataDome anti-bot bypass.

    Detects DataDome protection from cookies (``datadome``), JavaScript
    redirects, and response headers. Bypasses it via Playwright to obtain
    a valid ``datadome`` cookie.
    """

    DATADOME_INDICATORS = ['datadome', 'dd_']

    DATADOME_HEADER_INDICATORS = [
        'x-datadome',
        'x-dd-b',
        'x-dd-type',
    ]

    DATADOME_SCRIPT_PATTERNS = [
        re.compile(r'js\.datadome\.co', re.I),
        re.compile(r'datadome\.co/captcha', re.I),
        re.compile(r'dd\.[\w]+\.js', re.I),
    ]

    def __init__(self, browser_timeout: int = 30):
        self.browser_timeout = browser_timeout

    def detect(self, response: Response) -> bool:
        """Detect DataDome from cookies/JS redirects."""
        # Check cookies
        cookies = self._get_cookies(response)
        for indicator in self.DATADOME_INDICATORS:
            for cookie_name in cookies:
                if indicator in cookie_name.lower():
                    logger.debug("DataDome detected via cookie: %s", cookie_name)
                    return True

        # Check headers
        for header_name in self.DATADOME_HEADER_INDICATORS:
            if response.headers.get(header_name):
                logger.debug("DataDome detected via header: %s", header_name)
                return True

        # Check response body for DataDome script
        try:
            text = response.text[:10000]
        except Exception:
            return False

        for pattern in self.DATADOME_SCRIPT_PATTERNS:
            if pattern.search(text):
                logger.debug("DataDome detected via script pattern")
                return True

        # Check for DataDome captcha redirect (403 with geo.captcha-delivery.com)
        if response.status == 403:
            if 'captcha-delivery.com' in response.text[:5000]:
                logger.debug("DataDome detected via captcha redirect")
                return True

        return False

    def bypass(self, url: str) -> Optional[Dict[str, str]]:
        """
        Bypass DataDome using browser automation + cookie extraction.

        Loads the page in a headless Playwright browser, waits for the
        DataDome JS to complete, then extracts the ``datadome`` cookie.

        Returns:
            Dict of cookies on success, or None on failure.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed; cannot bypass DataDome")
            return None

        result: Dict[str, str] = {}
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ],
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/136.0.0.0 Safari/537.36'
                    ),
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=self.browser_timeout * 1000)

                # Wait for DataDome challenge resolution
                page.wait_for_timeout(5000)

                # Check if we got redirected to captcha page
                if 'captcha-delivery.com' in page.url:
                    logger.warning("DataDome: redirected to captcha page, automated bypass failed")
                    browser.close()
                    return None

                cookies = context.cookies()
                for cookie in cookies:
                    name_lower = cookie['name'].lower()
                    if any(ind in name_lower for ind in self.DATADOME_INDICATORS):
                        result[cookie['name']] = cookie['value']

                browser.close()

        except Exception as exc:
            logger.error("DataDome bypass failed: %s", exc)
            return None

        if result:
            logger.info("DataDome: extracted %d cookies from %s", len(result), url)
            return result

        logger.warning("DataDome: no cookies extracted from %s", url)
        return None

    @staticmethod
    def _get_cookies(response: Response) -> Dict[str, str]:
        """Extract cookies from a Scrapy response via Set-Cookie headers."""
        cookies: Dict[str, str] = {}
        for header_value in response.headers.getlist('Set-Cookie'):
            decoded = header_value.decode('utf-8', errors='replace')
            if '=' in decoded:
                name, _, rest = decoded.partition('=')
                value = rest.split(';', 1)[0]
                cookies[name.strip()] = value.strip()
        return cookies


# =============================================================================
# PERIMETERX / HUMAN BYPASS
# =============================================================================

class PerimeterXBypass:
    """
    PerimeterX/HUMAN anti-bot bypass.

    Detects PerimeterX protection via ``_px*`` cookies and characteristic
    block pages, then bypasses by extracting valid cookies from a Playwright
    session.
    """

    PX_INDICATORS = ['_px', '_pxhd', '_pxvid']

    PX_HEADER_INDICATORS = [
        'x-px-block',
        'x-px-captcha',
    ]

    PX_SCRIPT_PATTERNS = [
        re.compile(r'client\.perimeterx\.net', re.I),
        re.compile(r'captcha\.px-cdn\.net', re.I),
        re.compile(r'\/api\/v\d+\/collector', re.I),
    ]

    PX_BLOCK_PATTERNS = [
        re.compile(r'block\.perimeterx\.net', re.I),
        re.compile(r'Access to this page has been denied', re.I),
        re.compile(r'press & hold', re.I),  # HUMAN challenge prompt
        re.compile(r'_pxCaptcha', re.I),
    ]

    def __init__(self, browser_timeout: int = 30):
        self.browser_timeout = browser_timeout

    def detect(self, response: Response) -> bool:
        """Detect PerimeterX/HUMAN from cookies, headers, and body."""
        # Check cookies
        cookies = self._get_cookies(response)
        for indicator in self.PX_INDICATORS:
            for cookie_name in cookies:
                if cookie_name.startswith(indicator):
                    logger.debug("PerimeterX detected via cookie: %s", cookie_name)
                    return True

        # Check headers
        for header_name in self.PX_HEADER_INDICATORS:
            if response.headers.get(header_name):
                logger.debug("PerimeterX detected via header: %s", header_name)
                return True

        # Check body
        try:
            text = response.text[:10000]
        except Exception:
            return False

        for pattern in self.PX_SCRIPT_PATTERNS:
            if pattern.search(text):
                logger.debug("PerimeterX detected via script pattern")
                return True

        for pattern in self.PX_BLOCK_PATTERNS:
            if pattern.search(text):
                logger.debug("PerimeterX detected via block pattern")
                return True

        return False

    def bypass(self, url: str) -> Optional[Dict[str, str]]:
        """
        Bypass PerimeterX using browser automation + cookie extraction.

        Returns:
            Dict of PX cookies on success, or None on failure.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed; cannot bypass PerimeterX")
            return None

        result: Dict[str, str] = {}
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ],
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/136.0.0.0 Safari/537.36'
                    ),
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=self.browser_timeout * 1000)

                # Wait for PX validation to complete
                page.wait_for_timeout(5000)

                # Check if we are on a block page
                content = page.content()
                for pattern in self.PX_BLOCK_PATTERNS:
                    if pattern.search(content):
                        logger.warning("PerimeterX: still on block page, bypass failed")
                        browser.close()
                        return None

                cookies = context.cookies()
                px_prefixes = tuple(self.PX_INDICATORS)
                for cookie in cookies:
                    if cookie['name'].startswith(px_prefixes):
                        result[cookie['name']] = cookie['value']

                browser.close()

        except Exception as exc:
            logger.error("PerimeterX bypass failed: %s", exc)
            return None

        if result:
            logger.info("PerimeterX: extracted %d cookies from %s", len(result), url)
            return result

        logger.warning("PerimeterX: no cookies extracted from %s", url)
        return None

    @staticmethod
    def _get_cookies(response: Response) -> Dict[str, str]:
        """Extract cookies from a Scrapy response via Set-Cookie headers."""
        cookies: Dict[str, str] = {}
        for header_value in response.headers.getlist('Set-Cookie'):
            decoded = header_value.decode('utf-8', errors='replace')
            if '=' in decoded:
                name, _, rest = decoded.partition('=')
                value = rest.split(';', 1)[0]
                cookies[name.strip()] = value.strip()
        return cookies


# =============================================================================
# IMPERVA / INCAPSULA BYPASS
# =============================================================================

class IncapsulaBypass:
    """
    Imperva/Incapsula anti-bot bypass.

    Imperva uses multiple layers:
    - ___utmvc cookie (challenge validation)
    - incap_ses_* session cookies
    - visid_incap_* visitor ID cookies
    - reese84 JS challenge (newer versions)
    - JS injection detection via DOM checks
    """

    INCAPSULA_INDICATORS = [
        'incap_ses_',
        'visid_incap_',
        '___utmvc',
        'reese84',
        'incap_bl',
    ]

    INCAPSULA_HEADERS = [
        'x-iinfo',
        'x-cdn',
    ]

    INCAPSULA_PATTERNS = [
        r'/_Incapsula_Resource',
        r'incapsula\.com',
        r'Request unsuccessful.*Incapsula',
        r'robots\.txt.*Incapsula',
        r'reese84',
    ]

    def detect(self, response) -> bool:
        """Detect Incapsula from cookies, headers, and content."""
        # Check cookies
        cookies = {c.decode() if isinstance(c, bytes) else c for c in response.headers.getlist('Set-Cookie')}
        cookie_str = ' '.join(str(c) for c in cookies)
        if any(ind in cookie_str for ind in self.INCAPSULA_INDICATORS):
            return True
        # Check headers
        for header in self.INCAPSULA_HEADERS:
            if response.headers.get(header):
                val = response.headers.get(header, b'').decode('utf-8', errors='ignore')
                if 'incapsula' in val.lower() or 'imperva' in val.lower():
                    return True
        # Check content
        try:
            text = response.text[:5000]
            for pattern in self.INCAPSULA_PATTERNS:
                if re.search(pattern, text, re.I):
                    return True
        except Exception:
            pass
        return False

    def bypass(self, url: str) -> Optional[Dict[str, str]]:
        """Bypass Incapsula using browser automation + realistic behavior."""
        try:
            from scrapy_playwright.page import PageMethod
        except ImportError:
            pass

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                    locale='en-US',
                )
                page = context.new_page()

                # Navigate and wait for Incapsula JS to execute
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Simulate realistic behavior (Incapsula checks mouse/keyboard events)
                import random
                page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                page.wait_for_timeout(random.randint(500, 1500))
                page.mouse.move(random.randint(200, 900), random.randint(200, 500))
                page.evaluate('window.scrollBy(0, 300)')
                page.wait_for_timeout(random.randint(1000, 3000))

                # Extract cookies after JS execution
                cookies = context.cookies()
                result = {c['name']: c['value'] for c in cookies}

                browser.close()

                # Check we got the important cookies
                has_incap = any(k.startswith(('incap_ses_', 'visid_incap_', '___utmvc', 'reese84')) for k in result)
                if has_incap:
                    logger.info(f"Incapsula bypass success for {url}: got {len(result)} cookies")
                    return result

                logger.warning(f"Incapsula bypass: no Incapsula cookies obtained for {url}")
                return result  # Return whatever cookies we got

        except ImportError:
            logger.debug("Playwright not installed for Incapsula bypass")
            return None
        except Exception as e:
            logger.warning(f"Incapsula bypass failed for {url}: {e}")
            return None


# =============================================================================
# SCRAPY MIDDLEWARE
# =============================================================================

class CaptchaBypassMiddleware:
    """
    Scrapy middleware integrating all bypass systems.

    Automatically detects the protection type on each response and delegates
    to the appropriate bypass handler:

        - CAPTCHA (reCAPTCHA, hCaptcha, Turnstile) -> CaptchaSolver
        - Akamai Bot Manager -> AkamaiBypass
        - DataDome -> DataDomeBypass
        - PerimeterX/HUMAN -> PerimeterXBypass
        - Imperva/Incapsula -> IncapsulaBypass

    Settings:
        CAPTCHA_ENABLED            (bool, default False)
        CAPTCHA_PROVIDER           (str, default 'capsolver')
        CAPTCHA_API_KEY            (str, default '' - prefer env var CAPTCHA_API_KEY)
        CAPTCHA_POLL_INTERVAL      (float, default 3.0)
        CAPTCHA_MAX_TIMEOUT        (int, default 120)
        CAPTCHA_MAX_RETRIES        (int, default 2)
        AKAMAI_BYPASS_ENABLED      (bool, default False)
        DATADOME_BYPASS_ENABLED    (bool, default False)
        PERIMETERX_BYPASS_ENABLED  (bool, default False)
        INCAPSULA_BYPASS_ENABLED   (bool, default False)
    """

    def __init__(
        self,
        captcha_enabled: bool = False,
        captcha_provider: str = 'capsolver',
        captcha_api_key: str = '',
        captcha_poll_interval: float = 3.0,
        captcha_max_timeout: int = 120,
        captcha_max_retries: int = 2,
        akamai_enabled: bool = False,
        datadome_enabled: bool = False,
        perimeterx_enabled: bool = False,
        incapsula_enabled: bool = False,
    ):
        self.captcha_enabled = captcha_enabled
        self.akamai_enabled = akamai_enabled
        self.datadome_enabled = datadome_enabled
        self.perimeterx_enabled = perimeterx_enabled
        self.incapsula_enabled = incapsula_enabled
        self.max_retries = captcha_max_retries

        # Initialize sub-systems lazily
        self.solver: Optional[CaptchaSolver] = None
        if self.captcha_enabled:
            self.solver = CaptchaSolver(
                provider=captcha_provider,
                api_key=captcha_api_key,
                poll_interval=captcha_poll_interval,
                max_timeout=captcha_max_timeout,
            )

        self.akamai: Optional[AkamaiBypass] = None
        if self.akamai_enabled:
            self.akamai = AkamaiBypass()

        self.datadome: Optional[DataDomeBypass] = None
        if self.datadome_enabled:
            self.datadome = DataDomeBypass()

        self.perimeterx: Optional[PerimeterXBypass] = None
        if self.perimeterx_enabled:
            self.perimeterx = PerimeterXBypass()

        self.incapsula_bypass: Optional[IncapsulaBypass] = None
        if self.incapsula_enabled:
            self.incapsula_bypass = IncapsulaBypass()

        # Stats counters
        self.stats: Dict[str, int] = {
            'captchas_detected': 0,
            'captchas_solved': 0,
            'captchas_failed': 0,
            'akamai_detected': 0,
            'akamai_bypassed': 0,
            'akamai_failed': 0,
            'datadome_detected': 0,
            'datadome_bypassed': 0,
            'datadome_failed': 0,
            'perimeterx_detected': 0,
            'perimeterx_bypassed': 0,
            'perimeterx_failed': 0,
            'incapsula_detected': 0,
            'incapsula_bypassed': 0,
            'incapsula_failed': 0,
        }

    @classmethod
    def from_crawler(cls, crawler):
        captcha_enabled = crawler.settings.getbool('CAPTCHA_ENABLED', False)
        akamai_enabled = crawler.settings.getbool('AKAMAI_BYPASS_ENABLED', False)
        datadome_enabled = crawler.settings.getbool('DATADOME_BYPASS_ENABLED', False)
        perimeterx_enabled = crawler.settings.getbool('PERIMETERX_BYPASS_ENABLED', False)
        incapsula_enabled = crawler.settings.getbool('INCAPSULA_BYPASS_ENABLED', False)

        if not any([captcha_enabled, akamai_enabled, datadome_enabled, perimeterx_enabled, incapsula_enabled]):
            raise NotConfigured(
                "CaptchaBypassMiddleware: all bypass systems disabled"
            )

        api_key = (
            crawler.settings.get('CAPTCHA_API_KEY', '')
            or os.getenv('CAPTCHA_API_KEY', '')
        )

        middleware = cls(
            captcha_enabled=captcha_enabled,
            captcha_provider=crawler.settings.get('CAPTCHA_PROVIDER', 'capsolver'),
            captcha_api_key=api_key,
            captcha_poll_interval=crawler.settings.getfloat('CAPTCHA_POLL_INTERVAL', 3.0),
            captcha_max_timeout=crawler.settings.getint('CAPTCHA_MAX_TIMEOUT', 120),
            captcha_max_retries=crawler.settings.getint('CAPTCHA_MAX_RETRIES', 2),
            akamai_enabled=akamai_enabled,
            datadome_enabled=datadome_enabled,
            perimeterx_enabled=perimeterx_enabled,
            incapsula_enabled=incapsula_enabled,
        )

        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    # ------------------------------------------------------------------
    # Response processing
    # ------------------------------------------------------------------

    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Detect protection type and apply appropriate bypass."""
        attempt = request.meta.get('_captcha_bypass_attempt', 0)
        if attempt >= self.max_retries:
            return response

        # 1. Akamai detection
        if self.akamai_enabled and self.akamai:
            if self.akamai.detect(response):
                self.stats['akamai_detected'] += 1
                logger.info("Akamai protection detected on %s", request.url)
                new_request = self._handle_akamai(request, spider)
                if new_request:
                    return new_request

        # 2. DataDome detection
        if self.datadome_enabled and self.datadome:
            if self.datadome.detect(response):
                self.stats['datadome_detected'] += 1
                logger.info("DataDome protection detected on %s", request.url)
                new_request = self._handle_datadome(request, spider)
                if new_request:
                    return new_request

        # 3. PerimeterX detection
        if self.perimeterx_enabled and self.perimeterx:
            if self.perimeterx.detect(response):
                self.stats['perimeterx_detected'] += 1
                logger.info("PerimeterX protection detected on %s", request.url)
                new_request = self._handle_perimeterx(request, spider)
                if new_request:
                    return new_request

        # 4. Incapsula detection
        if self.incapsula_enabled and self.incapsula_bypass:
            if self.incapsula_bypass.detect(response):
                self.stats['incapsula_detected'] += 1
                logger.info("Incapsula protection detected on %s", request.url)
                new_request = self._handle_incapsula(request, spider)
                if new_request:
                    return new_request

        # 5. CAPTCHA detection
        if self.captcha_enabled and self.solver:
            try:
                text = response.text
            except Exception:
                return response

            captcha_type, site_key = detect_captcha_type(text)
            if captcha_type and site_key:
                self.stats['captchas_detected'] += 1
                logger.info(
                    "CAPTCHA detected: type=%s key=%s on %s",
                    captcha_type, site_key, request.url,
                )
                new_request = self._handle_captcha(
                    request, spider, captcha_type, site_key,
                )
                if new_request:
                    return new_request

        return response

    # ------------------------------------------------------------------
    # Individual handlers
    # ------------------------------------------------------------------

    def _handle_captcha(
        self,
        request: Request,
        spider,
        captcha_type: str,
        site_key: str,
    ) -> Optional[Request]:
        """Solve CAPTCHA and retry the request with the token."""
        token: Optional[str] = None

        try:
            if captcha_type == 'recaptcha_v2':
                token = self.solver.solve_recaptcha_v2(site_key, request.url)
            elif captcha_type == 'recaptcha_v3':
                token = self.solver.solve_recaptcha_v3(site_key, request.url)
            elif captcha_type == 'hcaptcha':
                token = self.solver.solve_hcaptcha(site_key, request.url)
            elif captcha_type == 'turnstile':
                token = self.solver.solve_turnstile(site_key, request.url)
        except Exception as exc:
            logger.error("CAPTCHA solve error: %s", exc)

        if token:
            self.stats['captchas_solved'] += 1
            spider.logger.info("CAPTCHA solved for %s", request.url)

            attempt = request.meta.get('_captcha_bypass_attempt', 0)
            return request.replace(
                meta={
                    **request.meta,
                    '_captcha_bypass_attempt': attempt + 1,
                    '_captcha_token': token,
                    '_captcha_type': captcha_type,
                },
                dont_filter=True,
            )

        self.stats['captchas_failed'] += 1
        spider.logger.warning("CAPTCHA solving failed for %s", request.url)
        return None

    def _handle_akamai(self, request: Request, spider) -> Optional[Request]:
        """Bypass Akamai and retry request with valid cookies."""
        cookies = self.akamai.get_valid_cookies(request.url)

        if cookies:
            self.stats['akamai_bypassed'] += 1
            spider.logger.info("Akamai bypassed for %s", request.url)

            attempt = request.meta.get('_captcha_bypass_attempt', 0)
            return request.replace(
                cookies={**dict(request.cookies or {}), **cookies},
                meta={
                    **request.meta,
                    '_captcha_bypass_attempt': attempt + 1,
                },
                dont_filter=True,
            )

        self.stats['akamai_failed'] += 1
        spider.logger.warning("Akamai bypass failed for %s", request.url)
        return None

    def _handle_datadome(self, request: Request, spider) -> Optional[Request]:
        """Bypass DataDome and retry request with valid cookies."""
        cookies = self.datadome.bypass(request.url)

        if cookies:
            self.stats['datadome_bypassed'] += 1
            spider.logger.info("DataDome bypassed for %s", request.url)

            attempt = request.meta.get('_captcha_bypass_attempt', 0)
            return request.replace(
                cookies={**dict(request.cookies or {}), **cookies},
                meta={
                    **request.meta,
                    '_captcha_bypass_attempt': attempt + 1,
                },
                dont_filter=True,
            )

        self.stats['datadome_failed'] += 1
        spider.logger.warning("DataDome bypass failed for %s", request.url)
        return None

    def _handle_perimeterx(self, request: Request, spider) -> Optional[Request]:
        """Bypass PerimeterX and retry request with valid cookies."""
        cookies = self.perimeterx.bypass(request.url)

        if cookies:
            self.stats['perimeterx_bypassed'] += 1
            spider.logger.info("PerimeterX bypassed for %s", request.url)

            attempt = request.meta.get('_captcha_bypass_attempt', 0)
            return request.replace(
                cookies={**dict(request.cookies or {}), **cookies},
                meta={
                    **request.meta,
                    '_captcha_bypass_attempt': attempt + 1,
                },
                dont_filter=True,
            )

        self.stats['perimeterx_failed'] += 1
        spider.logger.warning("PerimeterX bypass failed for %s", request.url)
        return None

    def _handle_incapsula(self, request: Request, spider) -> Optional[Request]:
        """Bypass Incapsula and retry request with valid cookies."""
        cookies = self.incapsula_bypass.bypass(request.url)

        if cookies:
            self.stats['incapsula_bypassed'] += 1
            spider.logger.info("Incapsula bypassed for %s", request.url)

            attempt = request.meta.get('_captcha_bypass_attempt', 0)
            return request.replace(
                cookies={**dict(request.cookies or {}), **cookies},
                meta={
                    **request.meta,
                    '_captcha_bypass_attempt': attempt + 1,
                },
                dont_filter=True,
            )

        self.stats['incapsula_failed'] += 1
        spider.logger.warning("Incapsula bypass failed for %s", request.url)
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def spider_closed(self, spider, reason):
        """Log bypass statistics on spider close."""
        has_activity = any(v > 0 for v in self.stats.values())
        if not has_activity:
            return

        spider.logger.info(
            "CaptchaBypass Stats: "
            "CAPTCHA(detected=%d, solved=%d, failed=%d) "
            "Akamai(detected=%d, bypassed=%d, failed=%d) "
            "DataDome(detected=%d, bypassed=%d, failed=%d) "
            "PerimeterX(detected=%d, bypassed=%d, failed=%d) "
            "Incapsula(detected=%d, bypassed=%d, failed=%d)",
            self.stats['captchas_detected'],
            self.stats['captchas_solved'],
            self.stats['captchas_failed'],
            self.stats['akamai_detected'],
            self.stats['akamai_bypassed'],
            self.stats['akamai_failed'],
            self.stats['datadome_detected'],
            self.stats['datadome_bypassed'],
            self.stats['datadome_failed'],
            self.stats['perimeterx_detected'],
            self.stats['perimeterx_bypassed'],
            self.stats['perimeterx_failed'],
            self.stats['incapsula_detected'],
            self.stats['incapsula_bypassed'],
            self.stats['incapsula_failed'],
        )
