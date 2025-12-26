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

Usage:
    from BDNewsPaper.antibot import get_full_antibot_js, get_canvas_noise_js

Settings:
    ANTIBOT_ENABLED = True
    ANTIBOT_CANVAS_NOISE = True
    ANTIBOT_WEBGL_NOISE = True
"""

import random
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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
) -> str:
    """
    Get combined anti-bot JavaScript for Playwright.
    
    All features enabled by default for maximum protection.
    """
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
    
    combined = "\n\n".join(scripts)
    logger.debug(f"Generated anti-bot JS with {len(scripts)} modules, {len(combined)} chars")
    
    return combined


def get_antibot_playwright_options() -> Dict:
    """
    Get Playwright launch and context options for maximum anti-detection.
    """
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
                '--window-size=1920,1080',
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
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'Asia/Dhaka',
            'geolocation': {'latitude': 23.8103, 'longitude': 90.4125},
            'permissions': ['geolocation'],
            'color_scheme': 'light',
            'java_script_enabled': True,
            'ignore_https_errors': True,
        },
        'init_script': get_full_antibot_js(),
    }


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
