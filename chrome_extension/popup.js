// BD News Clipper - Popup Script

const API_URL_KEY = 'bdnews_api_url';
const STATS_KEY = 'bdnews_clip_stats';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    const settings = await chrome.storage.sync.get([API_URL_KEY, STATS_KEY]);

    if (settings[API_URL_KEY]) {
        document.getElementById('api-url').value = settings[API_URL_KEY];
    } else {
        document.getElementById('api-url').value = 'http://localhost:8000';
    }

    updateStats(settings[STATS_KEY] || { today: 0, total: 0 });
    analyzeCurrentPage();
});

// Analyze current page
async function analyzeCurrentPage() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (!tab.url) {
            showStatus('Cannot analyze this page', 'error');
            return;
        }

        // Check if news site
        const newsPatterns = [
            'prothomalo.com', 'thedailystar.net', 'kalerkantho.com',
            'bdnews24.com', 'jugantor.com', 'dhakatribune.com',
            'ittefaq.com.bd', 'banglanews24.com'
        ];

        const isNewsSite = newsPatterns.some(p => tab.url.includes(p));

        if (!isNewsSite) {
            showStatus('Not a supported news site', 'info');
            return;
        }

        // Get article data from content script
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'extract' });

        if (response && response.headline) {
            showArticlePreview(response);
            document.getElementById('clip-btn').disabled = false;
            showStatus('Ready to clip', 'success');
        } else {
            showStatus('No article found on this page', 'info');
        }

    } catch (error) {
        showStatus('Error analyzing page', 'error');
        console.error(error);
    }
}

// Show article preview
function showArticlePreview(article) {
    const preview = document.getElementById('article-preview');
    preview.style.display = 'block';

    document.getElementById('preview-title').textContent =
        article.headline.substring(0, 80) + (article.headline.length > 80 ? '...' : '');
    document.getElementById('preview-meta').textContent =
        `${article.paper_name || 'Unknown'} • ${article.category || 'News'}`;

    // Store for clipping
    preview.dataset.article = JSON.stringify(article);
}

// Clip article
document.getElementById('clip-btn').addEventListener('click', async () => {
    const btn = document.getElementById('clip-btn');
    const preview = document.getElementById('article-preview');

    if (!preview.dataset.article) {
        showStatus('No article to clip', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Clipping...';

    try {
        const article = JSON.parse(preview.dataset.article);
        const apiUrl = document.getElementById('api-url').value || 'http://localhost:8000';

        const response = await fetch(`${apiUrl}/articles/clip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(article)
        });

        if (response.ok) {
            showStatus('✅ Article clipped!', 'success');
            await incrementStats();
        } else {
            const error = await response.json();
            showStatus(`Error: ${error.detail || 'Failed'}`, 'error');
        }

    } catch (error) {
        showStatus('Cannot connect to API', 'error');
        console.error(error);
    }

    btn.disabled = false;
    btn.textContent = '📎 Clip Article';
});

// View dashboard
document.getElementById('view-db').addEventListener('click', () => {
    const apiUrl = document.getElementById('api-url').value || 'http://localhost:8000';
    chrome.tabs.create({ url: `${apiUrl}/docs` });
});

// Save settings
document.getElementById('save-settings').addEventListener('click', async () => {
    const apiUrl = document.getElementById('api-url').value;
    await chrome.storage.sync.set({ [API_URL_KEY]: apiUrl });
    showStatus('Settings saved', 'success');
});

// Helper functions
function showStatus(message, type = 'info') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;
}

function updateStats(stats) {
    document.getElementById('clips-today').textContent = stats.today || 0;
    document.getElementById('clips-total').textContent = stats.total || 0;
}

async function incrementStats() {
    const data = await chrome.storage.sync.get([STATS_KEY]);
    const stats = data[STATS_KEY] || { today: 0, total: 0, date: null };

    const today = new Date().toDateString();
    if (stats.date !== today) {
        stats.today = 0;
        stats.date = today;
    }

    stats.today++;
    stats.total++;

    await chrome.storage.sync.set({ [STATS_KEY]: stats });
    updateStats(stats);
}
