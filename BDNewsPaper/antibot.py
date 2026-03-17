"""
Anti-Bot Evasion Module
=======================
Advanced browser fingerprint randomization and anti-detection.

Features:
    - Canvas fingerprint randomization
    - WebGL fingerprint randomization
    - Audio context fingerprinting protection
    - Font enumeration protection
    - Screen/resolution randomization
    - BrowserForge coherent fingerprint generation (optional)
    - Behavioral simulation (mouse movement, scrolling)

Usage:
    from BDNewsPaper.antibot import get_full_antibot_js, get_canvas_noise_js
    from BDNewsPaper.antibot import generate_coherent_fingerprint

Settings:
    ANTIBOT_ENABLED = True
    ANTIBOT_CANVAS_NOISE = True
    ANTIBOT_WEBGL_NOISE = True
"""

import json
import random
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy import for BrowserForge
BROWSERFORGE_AVAILABLE = False
try:
    from browserforge.fingerprints import FingerprintGenerator
    BROWSERFORGE_AVAILABLE = True
except ImportError:
    FingerprintGenerator = None


# =============================================================================
# CANVAS FINGERPRINT RANDOMIZATION
# =============================================================================

CANVAS_NOISE_JS = """
// Canvas fingerprint noise injection
(function() {
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    
    // Add subtle noise to canvas data
    function addNoise(data) {
        for (let i = 0; i < data.length; i += 4) {
            // Add random noise to RGB values (subtle)
            data[i] = Math.min(255, Math.max(0, data[i] + (Math.random() * 2 - 1)));
            data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + (Math.random() * 2 - 1)));
            data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + (Math.random() * 2 - 1)));
        }
        return data;
    }
    
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const context = this.getContext('2d');
        if (context) {
            const imageData = originalGetImageData.call(context, 0, 0, this.width, this.height);
            addNoise(imageData.data);
            context.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, args);
    };
    
    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        const imageData = originalGetImageData.apply(this, args);
        addNoise(imageData.data);
        return imageData;
    };
    
    console.log('[AntiBot] Canvas fingerprint noise applied');
})();
"""


# =============================================================================
# WEBGL FINGERPRINT RANDOMIZATION
# =============================================================================

WEBGL_NOISE_JS = """
// WebGL fingerprint randomization
(function() {
    const vendors = [
        'Intel Inc.',
        'NVIDIA Corporation', 
        'AMD',
        'Google Inc.',
        'Apple Inc.',
    ];
    
    const renderers = [
        'Intel Iris OpenGL Engine',
        'NVIDIA GeForce GTX 1080',
        'AMD Radeon Pro 5500M',
        'ANGLE (Intel, Intel(R) UHD Graphics 630)',
        'Mesa DRI Intel(R) UHD Graphics 620',
    ];
    
    const selectedVendor = vendors[Math.floor(Math.random() * vendors.length)];
    const selectedRenderer = renderers[Math.floor(Math.random() * renderers.length)];
    
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) return selectedVendor;
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) return selectedRenderer;
            
            return target.apply(thisArg, args);
        }
    };
    
    // Proxy WebGLRenderingContext
    if (WebGLRenderingContext.prototype.getParameter) {
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            WebGLRenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    
    // Proxy WebGL2RenderingContext
    if (typeof WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter) {
        WebGL2RenderingContext.prototype.getParameter = new Proxy(
            WebGL2RenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    
    console.log('[AntiBot] WebGL fingerprint randomized:', selectedVendor, selectedRenderer);
})();
"""


# =============================================================================
# AUDIO CONTEXT FINGERPRINT PROTECTION
# =============================================================================

AUDIO_NOISE_JS = """
// AudioContext fingerprint noise
(function() {
    const originalGetChannelData = AudioBuffer.prototype.getChannelData;
    
    AudioBuffer.prototype.getChannelData = function(channel) {
        const array = originalGetChannelData.call(this, channel);
        // Add very subtle noise to audio fingerprint
        for (let i = 0; i < array.length; i += 100) {
            array[i] = array[i] + (Math.random() * 0.0001 - 0.00005);
        }
        return array;
    };
    
    console.log('[AntiBot] Audio fingerprint noise applied');
})();
"""


# =============================================================================
# SCREEN PROPERTIES RANDOMIZATION
# =============================================================================

SCREEN_RANDOMIZATION_JS = """
// Screen properties randomization
(function() {
    const screenResolutions = [
        {width: 1920, height: 1080},
        {width: 2560, height: 1440},
        {width: 1366, height: 768},
        {width: 1536, height: 864},
        {width: 1440, height: 900},
    ];
    
    const selectedRes = screenResolutions[Math.floor(Math.random() * screenResolutions.length)];
    const colorDepth = [24, 32][Math.floor(Math.random() * 2)];
    
    Object.defineProperty(screen, 'width', { get: () => selectedRes.width });
    Object.defineProperty(screen, 'height', { get: () => selectedRes.height });
    Object.defineProperty(screen, 'availWidth', { get: () => selectedRes.width });
    Object.defineProperty(screen, 'availHeight', { get: () => selectedRes.height - 40 });
    Object.defineProperty(screen, 'colorDepth', { get: () => colorDepth });
    Object.defineProperty(screen, 'pixelDepth', { get: () => colorDepth });
    
    // Randomize window inner dimensions slightly
    Object.defineProperty(window, 'innerWidth', { 
        get: () => selectedRes.width - Math.floor(Math.random() * 20),
        configurable: true 
    });
    Object.defineProperty(window, 'innerHeight', { 
        get: () => selectedRes.height - 100 - Math.floor(Math.random() * 20),
        configurable: true 
    });
    
    console.log('[AntiBot] Screen randomized:', selectedRes.width + 'x' + selectedRes.height);
})();
"""


# =============================================================================
# TIMEZONE AND LANGUAGE CONSISTENCY
# =============================================================================

LOCALE_CONSISTENCY_JS = """
// Timezone and language consistency for Bangladesh
(function() {
    // Override timezone offset (Bangladesh is UTC+6 = -360 minutes)
    Date.prototype.getTimezoneOffset = function() { return -360; };
    
    // Consistent timezone name
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(...args) {
        if (args.length === 0) args = ['en-US'];
        if (!args[1]) args[1] = {};
        args[1].timeZone = 'Asia/Dhaka';
        return new originalDateTimeFormat(...args);
    };
    
    // Override navigator language properties
    Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
    Object.defineProperty(navigator, 'languages', { 
        get: () => ['en-US', 'en', 'bn-BD', 'bn'] 
    });
    
    console.log('[AntiBot] Locale consistency applied (Asia/Dhaka)');
})();
"""


# =============================================================================
# HARDWARE CONCURRENCY RANDOMIZATION
# =============================================================================

HARDWARE_RANDOMIZATION_JS = """
// Hardware properties randomization
(function() {
    const cores = [4, 6, 8, 12, 16][Math.floor(Math.random() * 5)];
    const memory = [4, 8, 16, 32][Math.floor(Math.random() * 4)];
    
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => cores });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => memory });
    
    console.log('[AntiBot] Hardware randomized: ' + cores + ' cores, ' + memory + 'GB RAM');
})();
"""


# =============================================================================
# PLUGIN AND MIME TYPE SIMULATION
# =============================================================================

PLUGIN_SIMULATION_JS = """
// Plugin and MIME type simulation
(function() {
    const plugins = [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
    ];
    
    const mimeTypes = [
        { type: 'application/pdf', description: 'Portable Document Format', suffixes: 'pdf' },
        { type: 'application/x-google-chrome-pdf', description: 'Portable Document Format', suffixes: 'pdf' },
    ];
    
    // Create fake PluginArray
    const pluginArray = plugins.map((p, i) => {
        const plugin = { ...p, length: 1 };
        plugin[0] = mimeTypes[0];
        return plugin;
    });
    pluginArray.item = (i) => pluginArray[i];
    pluginArray.namedItem = (name) => pluginArray.find(p => p.name === name);
    pluginArray.refresh = () => {};
    
    Object.defineProperty(navigator, 'plugins', { get: () => pluginArray });
    
    console.log('[AntiBot] Plugins simulated: ' + plugins.length + ' plugins');
})();
"""


# =============================================================================
# WEBRTC LEAK PREVENTION
# =============================================================================

WEBRTC_PROTECTION_JS = """
// WebRTC leak prevention
(function() {
    // Disable WebRTC completely or return spoofed IPs
    const spoofedIP = '192.168.' + Math.floor(Math.random() * 256) + '.' + Math.floor(Math.random() * 256);
    
    if (typeof RTCPeerConnection !== 'undefined') {
        const originalRTCPeerConnection = RTCPeerConnection;
        
        RTCPeerConnection = function(...args) {
            const pc = new originalRTCPeerConnection(...args);
            
            // Override createDataChannel to prevent IP leak
            const originalCreateDataChannel = pc.createDataChannel.bind(pc);
            pc.createDataChannel = function(...dcArgs) {
                console.log('[AntiBot] WebRTC createDataChannel intercepted');
                return originalCreateDataChannel(...dcArgs);
            };
            
            // Override createOffer
            const originalCreateOffer = pc.createOffer.bind(pc);
            pc.createOffer = async function(...offerArgs) {
                const offer = await originalCreateOffer(...offerArgs);
                // Modify SDP to hide real IP
                if (offer.sdp) {
                    offer.sdp = offer.sdp.replace(/([0-9]{1,3}(\\.[0-9]{1,3}){3})/g, spoofedIP);
                }
                return offer;
            };
            
            return pc;
        };
        
        RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
    }
    
    console.log('[AntiBot] WebRTC protection enabled, spoofed IP:', spoofedIP);
})();
"""


# =============================================================================
# COMBINED ANTI-BOT SCRIPT
# =============================================================================

def get_full_antibot_js(
    canvas_noise: bool = True,
    webgl_noise: bool = True,
    audio_noise: bool = True,
    screen_random: bool = True,
    locale_consistency: bool = True,
    hardware_random: bool = True,
    plugin_simulation: bool = True,
    webrtc_protection: bool = True,
    behavioral_simulation: bool = True,
    use_coherent_profile: bool = True,
) -> str:
    """
    Get combined anti-bot JavaScript for Playwright.

    All features enabled by default for maximum protection.
    When use_coherent_profile=True and BrowserForge is available, generates
    statistically coherent fingerprints instead of independent random values.
    """
    if use_coherent_profile:
        return get_coherent_antibot_js()

    scripts = []

    if canvas_noise:
        scripts.append(CANVAS_NOISE_JS)
    if webgl_noise:
        scripts.append(WEBGL_NOISE_JS)
    if audio_noise:
        scripts.append(AUDIO_NOISE_JS)
    if screen_random:
        scripts.append(SCREEN_RANDOMIZATION_JS)
    if locale_consistency:
        scripts.append(LOCALE_CONSISTENCY_JS)
    if hardware_random:
        scripts.append(HARDWARE_RANDOMIZATION_JS)
    if plugin_simulation:
        scripts.append(PLUGIN_SIMULATION_JS)
    if webrtc_protection:
        scripts.append(WEBRTC_PROTECTION_JS)
    if behavioral_simulation:
        scripts.append(BEHAVIORAL_SIMULATION_JS)

    combined = "\n\n".join(scripts)
    logger.debug(f"Generated anti-bot JS with {len(scripts)} modules, {len(combined)} chars")

    return combined


def get_antibot_playwright_options() -> Dict:
    """
    Get Playwright launch and context options for maximum anti-detection.

    Uses BrowserForge coherent fingerprints when available to ensure
    screen resolution, GPU, CPU cores, and memory are statistically consistent.
    """
    profile = generate_coherent_fingerprint()
    ua = profile.get('userAgent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'

    return {
        'launch_options': {
            'headless': True,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-automation',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                f'--window-size={profile["width"]},{profile["height"]}',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-background-networking',
                '--disable-component-update',
                '--disable-sync',
                '--disable-translate',
                '--ignore-certificate-errors',
                '--start-maximized',
            ],
        },
        'context_options': {
            'viewport': {'width': profile['width'], 'height': profile['height']},
            'user_agent': ua,
            'locale': 'en-US',
            'timezone_id': 'Asia/Dhaka',
            'geolocation': {'latitude': 23.8103, 'longitude': 90.4125},
            'permissions': ['geolocation'],
            'color_scheme': 'light',
            'java_script_enabled': True,
            'ignore_https_errors': True,
        },
        'init_script': get_coherent_antibot_js(profile),
    }


# =============================================================================
# BROWSERFORGE COHERENT FINGERPRINT GENERATION
# =============================================================================

# Statistically coherent device profiles — used when BrowserForge is not installed.
# Each profile has GPU, screen, memory, and CPU that realistically co-occur.
COHERENT_DEVICE_PROFILES = [
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630)', 'width': 1920, 'height': 1080, 'cores': 8, 'memory': 16, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics)', 'width': 1920, 'height': 1080, 'cores': 8, 'memory': 16, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650)', 'width': 1920, 'height': 1080, 'cores': 8, 'memory': 16, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)', 'width': 2560, 'height': 1440, 'cores': 12, 'memory': 32, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (AMD, AMD Radeon RX 580)', 'width': 1920, 'height': 1080, 'cores': 8, 'memory': 16, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 620)', 'width': 1366, 'height': 768, 'cores': 4, 'memory': 8, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) HD Graphics 530)', 'width': 1536, 'height': 864, 'cores': 4, 'memory': 8, 'colorDepth': 24},
    {'vendor': 'Apple Inc.', 'renderer': 'Apple GPU', 'width': 1440, 'height': 900, 'cores': 8, 'memory': 8, 'colorDepth': 30},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4070)', 'width': 2560, 'height': 1440, 'cores': 16, 'memory': 32, 'colorDepth': 24},
    {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 770)', 'width': 1920, 'height': 1080, 'cores': 12, 'memory': 16, 'colorDepth': 24},
]


def _extract_browser_brand_list(user_agent: Optional[str]) -> List[Dict[str, str]]:
    """Extract sec-ch-ua brand list from user agent string.

    Parses the Chrome version from a UA string and builds a navigator.userAgentData
    brands list matching the Chrome 131+ client hints format.
    """
    if not user_agent:
        return [
            {'brand': 'Chromium', 'version': '133'},
            {'brand': 'Google Chrome', 'version': '133'},
            {'brand': 'Not?A_Brand', 'version': '99'},
        ]

    # Try to extract Chrome version
    import re
    chrome_match = re.search(r'Chrome/(\d+)', user_agent)
    if chrome_match:
        major = chrome_match.group(1)
        return [
            {'brand': 'Chromium', 'version': major},
            {'brand': 'Google Chrome', 'version': major},
            {'brand': 'Not?A_Brand', 'version': '99'},
        ]

    # Firefox
    ff_match = re.search(r'Firefox/(\d+)', user_agent)
    if ff_match:
        return [{'brand': 'Firefox', 'version': ff_match.group(1)}]

    # Safari
    safari_match = re.search(r'Version/(\d+)', user_agent)
    if safari_match and 'Safari' in user_agent:
        return [{'brand': 'Safari', 'version': safari_match.group(1)}]

    return [
        {'brand': 'Chromium', 'version': '133'},
        {'brand': 'Google Chrome', 'version': '133'},
        {'brand': 'Not?A_Brand', 'version': '99'},
    ]


def _build_client_hints_headers(profile: Dict) -> Dict[str, str]:
    """Build sec-ch-ua-* client hints headers matching the fingerprint.

    Returns headers dict with all Chrome 131+ client hints fields for
    consistent fingerprint presentation.
    """
    ua = profile.get('userAgent', '')
    brands = _extract_browser_brand_list(ua)

    # Build the sec-ch-ua header value
    brand_parts = []
    for b in brands:
        brand_parts.append(f'"{b["brand"]}";v="{b["version"]}"')
    sec_ch_ua = ', '.join(brand_parts)

    # Detect platform from UA or profile
    platform = 'Windows'
    if ua:
        if 'Macintosh' in ua or 'Mac OS' in ua:
            platform = 'macOS'
        elif 'Linux' in ua:
            platform = 'Linux'
        elif 'Android' in ua:
            platform = 'Android'

    # Detect mobile
    mobile = '?1' if 'Mobile' in (ua or '') else '?0'

    # Full version for sec-ch-ua-full-version-list
    import re
    full_version = '133.0.0.0'
    chrome_match = re.search(r'Chrome/([\d.]+)', ua or '')
    if chrome_match:
        full_version = chrome_match.group(1)

    full_brand_parts = []
    for b in brands:
        v = full_version if b['brand'] in ('Chromium', 'Google Chrome') else f'{b["version"]}.0.0.0'
        full_brand_parts.append(f'"{b["brand"]}";v="{v}"')

    return {
        'sec-ch-ua': sec_ch_ua,
        'sec-ch-ua-mobile': mobile,
        'sec-ch-ua-platform': f'"{platform}"',
        'sec-ch-ua-full-version-list': ', '.join(full_brand_parts),
        'sec-ch-ua-arch': '"x86"' if platform != 'Android' else '"arm"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-wow64': '?0',
    }


def _get_webgl_for_browser(user_agent: Optional[str], profile: Dict) -> Dict[str, str]:
    """Get consistent GPU/WebGL vendor strings matching the browser profile.

    For Chrome-based browsers, WebGL vendor is 'Google Inc.' with ANGLE renderer.
    For Firefox, vendor is the GPU maker directly.
    For Safari/macOS, vendor is 'Apple Inc.'.
    """
    ua = user_agent or ''

    # If profile already has good vendor/renderer from BrowserForge, keep them
    if profile.get('vendor') and profile.get('renderer'):
        return {'vendor': profile['vendor'], 'renderer': profile['renderer']}

    if 'Firefox' in ua:
        return {'vendor': 'Mozilla', 'renderer': 'Mozilla'}
    if 'Safari' in ua and 'Chrome' not in ua:
        return {'vendor': 'Apple Inc.', 'renderer': 'Apple GPU'}

    # Default Chrome/Chromium
    return {'vendor': 'Google Inc.', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630)'}


def generate_coherent_fingerprint() -> Dict:
    """
    Generate a statistically coherent browser fingerprint.

    Uses BrowserForge if installed (Bayesian model trained on real browser traffic),
    otherwise falls back to curated device profiles with realistic co-occurrences.

    The returned profile includes:
    - Core device properties: vendor, renderer, width, height, cores, memory, colorDepth
    - User agent and browser identification
    - sec-ch-ua-* client hints headers matching the fingerprint (Chrome 131+ format)
    - navigator.userAgentData brand list matching the browser profile
    - Consistent GPU/WebGL vendor strings matching the fingerprint's browser

    Returns:
        Dict with keys: vendor, renderer, width, height, cores, memory, colorDepth,
        userAgent, clientHints, brandList, webgl
    """
    if BROWSERFORGE_AVAILABLE:
        try:
            gen = FingerprintGenerator()
            fp = gen.generate()
            screen = fp.screen if hasattr(fp, 'screen') else None
            navigator = fp.navigator if hasattr(fp, 'navigator') else None

            profile = {
                'vendor': getattr(fp, 'webgl_vendor', 'Google Inc.') if hasattr(fp, 'webgl_vendor') else 'Google Inc.',
                'renderer': getattr(fp, 'webgl_renderer', 'ANGLE (Intel, Intel(R) UHD Graphics 630)') if hasattr(fp, 'webgl_renderer') else 'ANGLE (Intel, Intel(R) UHD Graphics 630)',
                'width': getattr(screen, 'width', 1920) if screen else 1920,
                'height': getattr(screen, 'height', 1080) if screen else 1080,
                'cores': getattr(navigator, 'hardwareConcurrency', 8) if navigator else 8,
                'memory': getattr(navigator, 'deviceMemory', 16) if navigator else 16,
                'colorDepth': getattr(screen, 'colorDepth', 24) if screen else 24,
                'userAgent': getattr(navigator, 'userAgent', None) if navigator else None,
            }

            # Enrich with 2026 client hints and consistent GPU strings
            profile['clientHints'] = _build_client_hints_headers(profile)
            profile['brandList'] = _extract_browser_brand_list(profile.get('userAgent'))
            webgl = _get_webgl_for_browser(profile.get('userAgent'), profile)
            profile['vendor'] = webgl['vendor']
            profile['renderer'] = webgl['renderer']
            profile['webgl'] = webgl

            logger.debug(f"BrowserForge fingerprint: {profile['renderer']}, {profile['width']}x{profile['height']}")
            return profile
        except Exception as e:
            logger.debug(f"BrowserForge generation failed, using built-in profiles: {e}")

    # Fallback: use curated coherent profiles
    profile = random.choice(COHERENT_DEVICE_PROFILES).copy()

    # Enrich fallback with client hints and brand list
    profile['clientHints'] = _build_client_hints_headers(profile)
    profile['brandList'] = _extract_browser_brand_list(profile.get('userAgent'))
    webgl = _get_webgl_for_browser(profile.get('userAgent'), profile)
    profile['vendor'] = webgl['vendor']
    profile['renderer'] = webgl['renderer']
    profile['webgl'] = webgl

    logger.debug(f"Coherent profile: {profile['renderer']}, {profile['width']}x{profile['height']}")
    return profile


def get_coherent_antibot_js(profile: Optional[Dict] = None) -> str:
    """
    Generate anti-bot JS using a coherent fingerprint profile instead of
    independent random values.

    Args:
        profile: Optional coherent fingerprint dict. If None, generates one.

    Returns:
        Combined JavaScript string for Playwright init_script.
    """
    if profile is None:
        profile = generate_coherent_fingerprint()

    # Build WebGL script with coherent GPU
    webgl_js = f"""
(function() {{
    const vendor = {json.dumps(profile['vendor'])};
    const renderer = {json.dumps(profile['renderer'])};
    const handler = {{
        apply: function(target, thisArg, args) {{
            if (args[0] === 37445) return vendor;
            if (args[0] === 37446) return renderer;
            return target.apply(thisArg, args);
        }}
    }};
    if (WebGLRenderingContext.prototype.getParameter)
        WebGLRenderingContext.prototype.getParameter = new Proxy(WebGLRenderingContext.prototype.getParameter, handler);
    if (typeof WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter)
        WebGL2RenderingContext.prototype.getParameter = new Proxy(WebGL2RenderingContext.prototype.getParameter, handler);
}})();"""

    # Build screen script with coherent resolution
    w, h = profile['width'], profile['height']
    cd = profile['colorDepth']
    screen_js = f"""
(function() {{
    Object.defineProperty(screen, 'width', {{ get: () => {w} }});
    Object.defineProperty(screen, 'height', {{ get: () => {h} }});
    Object.defineProperty(screen, 'availWidth', {{ get: () => {w} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {h - 40} }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {cd} }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {cd} }});
    Object.defineProperty(window, 'innerWidth', {{ get: () => {w - random.randint(0, 15)}, configurable: true }});
    Object.defineProperty(window, 'innerHeight', {{ get: () => {h - 100 - random.randint(0, 15)}, configurable: true }});
}})();"""

    # Build hardware script with coherent CPU/memory
    hw_js = f"""
(function() {{
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {profile['cores']} }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {profile['memory']} }});
}})();"""

    # Build navigator.userAgentData with brand list matching sec-ch-ua headers
    brand_list = profile.get('brandList', [
        {'brand': 'Chromium', 'version': '133'},
        {'brand': 'Google Chrome', 'version': '133'},
        {'brand': 'Not?A_Brand', 'version': '99'},
    ])
    client_hints = profile.get('clientHints', {})
    platform_name = client_hints.get('sec-ch-ua-platform', '"Windows"').strip('"')
    is_mobile = client_hints.get('sec-ch-ua-mobile', '?0') == '?1'

    ua_data_js = f"""
(function() {{
    // navigator.userAgentData brand list matching sec-ch-ua client hints
    const brands = {json.dumps(brand_list)};
    const platform = {json.dumps(platform_name)};
    const mobile = {json.dumps(is_mobile)};

    if (navigator.userAgentData !== undefined || 'userAgentData' in navigator) {{
        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => ({{
                brands: brands,
                mobile: mobile,
                platform: platform,
                getHighEntropyValues: (hints) => Promise.resolve({{
                    brands: brands,
                    mobile: mobile,
                    platform: platform,
                    architecture: 'x86',
                    bitness: '64',
                    model: '',
                    platformVersion: '15.0.0',
                    uaFullVersion: brands[0] ? brands[0].version + '.0.0.0' : '133.0.0.0',
                    fullVersionList: brands.map(b => ({{...b, version: b.version + '.0.0.0'}})),
                    wow64: false,
                }}),
                toJSON: () => ({{ brands: brands, mobile: mobile, platform: platform }}),
            }}),
            configurable: true,
        }});
    }}
    console.log('[AntiBot] userAgentData client hints applied');
}})();"""

    scripts = [
        CANVAS_NOISE_JS,
        webgl_js,
        AUDIO_NOISE_JS,
        screen_js,
        LOCALE_CONSISTENCY_JS,
        hw_js,
        ua_data_js,
        PLUGIN_SIMULATION_JS,
        WEBRTC_PROTECTION_JS,
        BEHAVIORAL_SIMULATION_JS,
    ]

    return "\n\n".join(scripts)


# =============================================================================
# BEHAVIORAL SIMULATION (mouse movement, scrolling)
# =============================================================================

BEHAVIORAL_SIMULATION_JS = """
// Behavioral simulation — synthetic human-like interactions
// Adds realistic mouse movement and scroll patterns to defeat behavioral analysis
(function() {
    // Generate Bezier curve points for natural mouse movement
    function bezierPoint(t, p0, p1, p2, p3) {
        const u = 1 - t;
        return u*u*u*p0 + 3*u*u*t*p1 + 3*u*t*t*p2 + t*t*t*p3;
    }

    let lastX = Math.random() * window.innerWidth * 0.6 + window.innerWidth * 0.2;
    let lastY = Math.random() * window.innerHeight * 0.6 + window.innerHeight * 0.2;
    let moveCount = 0;

    function simulateMouseMove() {
        if (moveCount > 20) return; // Don't overdo it
        moveCount++;

        const targetX = Math.random() * window.innerWidth * 0.8 + window.innerWidth * 0.1;
        const targetY = Math.random() * window.innerHeight * 0.8 + window.innerHeight * 0.1;

        // Control points for Bezier curve (creates natural arc)
        const cp1x = lastX + (targetX - lastX) * 0.3 + (Math.random() - 0.5) * 100;
        const cp1y = lastY + (targetY - lastY) * 0.1 + (Math.random() - 0.5) * 100;
        const cp2x = lastX + (targetX - lastX) * 0.7 + (Math.random() - 0.5) * 50;
        const cp2y = lastY + (targetY - lastY) * 0.9 + (Math.random() - 0.5) * 50;

        const steps = 8 + Math.floor(Math.random() * 8);
        let step = 0;

        function doStep() {
            if (step >= steps) {
                lastX = targetX;
                lastY = targetY;
                // Schedule next move with random delay (2-8 seconds)
                setTimeout(simulateMouseMove, 2000 + Math.random() * 6000);
                return;
            }
            const t = step / steps;
            const x = bezierPoint(t, lastX, cp1x, cp2x, targetX);
            const y = bezierPoint(t, lastY, cp1y, cp2y, targetY);

            window.dispatchEvent(new MouseEvent('mousemove', {
                clientX: x, clientY: y, bubbles: true
            }));

            step++;
            setTimeout(doStep, 20 + Math.random() * 40);
        }
        doStep();
    }

    // Start mouse simulation after a natural delay
    setTimeout(simulateMouseMove, 1500 + Math.random() * 3000);

    // Simulate occasional scrolling
    let scrollCount = 0;
    function simulateScroll() {
        if (scrollCount > 5) return;
        scrollCount++;

        const scrollAmount = 100 + Math.floor(Math.random() * 300);
        const direction = Math.random() > 0.3 ? 1 : -1; // 70% down, 30% up

        let scrolled = 0;
        function doScroll() {
            if (scrolled >= scrollAmount) {
                setTimeout(simulateScroll, 3000 + Math.random() * 8000);
                return;
            }
            const chunk = 20 + Math.floor(Math.random() * 40);
            window.scrollBy(0, chunk * direction);
            scrolled += chunk;
            setTimeout(doScroll, 30 + Math.random() * 50);
        }
        doScroll();
    }

    setTimeout(simulateScroll, 3000 + Math.random() * 5000);
})();
"""


# =============================================================================
# EXPORTS
# =============================================================================

# Individual scripts for granular use
get_canvas_noise_js = lambda: CANVAS_NOISE_JS
get_webgl_noise_js = lambda: WEBGL_NOISE_JS
get_audio_noise_js = lambda: AUDIO_NOISE_JS
get_screen_randomization_js = lambda: SCREEN_RANDOMIZATION_JS
get_locale_consistency_js = lambda: LOCALE_CONSISTENCY_JS
get_hardware_randomization_js = lambda: HARDWARE_RANDOMIZATION_JS
get_plugin_simulation_js = lambda: PLUGIN_SIMULATION_JS
get_webrtc_protection_js = lambda: WEBRTC_PROTECTION_JS
get_behavioral_simulation_js = lambda: BEHAVIORAL_SIMULATION_JS
