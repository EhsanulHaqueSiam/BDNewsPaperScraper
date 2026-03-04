// BD News Clipper - Background Service Worker

// Context menu for right-click clipping
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: 'clip-article',
        title: '📎 Clip to BD News',
        contexts: ['page', 'selection']
    });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'clip-article') {
        chrome.tabs.sendMessage(tab.id, { action: 'extract' }, async (response) => {
            if (response && response.headline) {
                // Show notification
                chrome.notifications.create({
                    type: 'basic',
                    iconUrl: 'icons/icon48.png',
                    title: 'BD News Clipper',
                    message: `Clipping: ${response.headline.substring(0, 50)}...`
                });

                // Try to clip
                try {
                    const settings = await chrome.storage.sync.get(['bdnews_api_url']);
                    const apiUrl = settings.bdnews_api_url || 'http://localhost:8000';

                    const res = await fetch(`${apiUrl}/articles/clip`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(response)
                    });

                    if (res.ok) {
                        chrome.notifications.create({
                            type: 'basic',
                            iconUrl: 'icons/icon48.png',
                            title: '✅ Clipped!',
                            message: 'Article saved to database'
                        });
                    }
                } catch (error) {
                    console.error('Clip failed:', error);
                }
            }
        });
    }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'openPopup') {
        chrome.action.openPopup();
    }
    return true;
});

// Badge to show clip count
async function updateBadge() {
    const data = await chrome.storage.sync.get(['bdnews_clip_stats']);
    const stats = data.bdnews_clip_stats || { today: 0 };

    if (stats.today > 0) {
        chrome.action.setBadgeText({ text: String(stats.today) });
        chrome.action.setBadgeBackgroundColor({ color: '#667eea' });
    } else {
        chrome.action.setBadgeText({ text: '' });
    }
}

// Update badge on stats change
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'sync' && changes.bdnews_clip_stats) {
        updateBadge();
    }
});

// Initial badge update
updateBadge();
