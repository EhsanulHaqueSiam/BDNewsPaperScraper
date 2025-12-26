// BD News Clipper - Content Script
// Extracts article data from news pages

(function () {
    // Article extraction configurations per site
    const extractors = {
        'prothomalo.com': {
            headline: 'h1.title, h1[itemprop="headline"]',
            body: '.story-content, article p',
            author: '.author-name, [rel="author"]',
            date: 'time[datetime], .published-time',
            category: '.category-name, .breadcrumb a:last-child'
        },
        'thedailystar.net': {
            headline: 'h1.story-headline, h1.article-title',
            body: '.article-content p, .story-body p',
            author: '.author a, .reporter-name',
            date: 'time[datetime], .time',
            category: '.section-tag a, .category'
        },
        'kalerkantho.com': {
            headline: 'h1.headline, h1.content-title',
            body: '.news-content p, .article-body p',
            author: '.reporter, .author',
            date: '.time, time',
            category: '.category, .section-name'
        },
        'bdnews24.com': {
            headline: 'h1.article-title, h1.headline',
            body: '.article-content p',
            author: '.author-name',
            date: '.article-date, time',
            category: '.category-name'
        },
        'default': {
            headline: 'h1, article h1, .headline',
            body: 'article p, .content p, .article-body p',
            author: '.author, [rel="author"], .by-line',
            date: 'time[datetime], .date, .published',
            category: '.category, .section, nav a'
        }
    };

    // Get extractor for current site
    function getExtractor() {
        const hostname = window.location.hostname;
        for (const [site, config] of Object.entries(extractors)) {
            if (hostname.includes(site)) {
                return config;
            }
        }
        return extractors.default;
    }

    // Extract text from selector
    function extractText(selector) {
        const el = document.querySelector(selector);
        return el ? el.textContent.trim() : null;
    }

    // Extract date
    function extractDate(selector) {
        const el = document.querySelector(selector);
        if (!el) return null;

        // Try datetime attribute first
        if (el.dateTime) return el.dateTime;
        if (el.getAttribute('datetime')) return el.getAttribute('datetime');

        return el.textContent.trim();
    }

    // Extract article body
    function extractBody(selector) {
        const elements = document.querySelectorAll(selector);
        if (!elements.length) return null;

        return Array.from(elements)
            .map(el => el.textContent.trim())
            .filter(text => text.length > 20) // Skip short paragraphs
            .join('\n\n');
    }

    // Main extraction function
    function extractArticle() {
        const config = getExtractor();

        const headline = extractText(config.headline);
        if (!headline) return null;

        const article = {
            url: window.location.href,
            headline: headline,
            article_body: extractBody(config.body),
            author: extractText(config.author),
            publication_date: extractDate(config.date),
            category: extractText(config.category),
            paper_name: getPaperName(),
            source_language: detectLanguage(headline),
            word_count: countWords(extractBody(config.body))
        };

        return article;
    }

    // Get paper name from hostname
    function getPaperName() {
        const hostname = window.location.hostname;
        const names = {
            'prothomalo.com': 'Prothom Alo',
            'thedailystar.net': 'The Daily Star',
            'kalerkantho.com': 'Kaler Kantho',
            'bdnews24.com': 'bdnews24',
            'jugantor.com': 'Jugantor',
            'dhakatribune.com': 'Dhaka Tribune',
            'ittefaq.com.bd': 'Daily Ittefaq',
            'banglanews24.com': 'Bangla News 24'
        };

        for (const [domain, name] of Object.entries(names)) {
            if (hostname.includes(domain)) return name;
        }

        return hostname.replace('www.', '').split('.')[0];
    }

    // Simple language detection
    function detectLanguage(text) {
        if (!text) return 'en';

        // Check for Bengali characters
        const bengaliPattern = /[\u0980-\u09FF]/;
        return bengaliPattern.test(text) ? 'bn' : 'en';
    }

    // Count words
    function countWords(text) {
        if (!text) return 0;
        return text.split(/\s+/).filter(w => w.length > 0).length;
    }

    // Listen for messages from popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'extract') {
            const article = extractArticle();
            sendResponse(article);
        }
        return true;
    });

    // Add visual indicator when on supported page
    function addClipIndicator() {
        if (!extractArticle()) return;

        const indicator = document.createElement('div');
        indicator.id = 'bdnews-clip-indicator';
        indicator.innerHTML = '📎';
        indicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            cursor: pointer;
            z-index: 99999;
            transition: transform 0.2s;
        `;

        indicator.addEventListener('mouseover', () => {
            indicator.style.transform = 'scale(1.1)';
        });

        indicator.addEventListener('mouseout', () => {
            indicator.style.transform = 'scale(1)';
        });

        indicator.addEventListener('click', () => {
            // Trigger popup
            chrome.runtime.sendMessage({ action: 'openPopup' });
        });

        document.body.appendChild(indicator);
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addClipIndicator);
    } else {
        addClipIndicator();
    }
})();
