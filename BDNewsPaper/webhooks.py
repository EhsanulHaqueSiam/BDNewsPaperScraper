"""
Webhooks Module
===============
Send notifications when new articles are scraped.

Supports:
    - HTTP webhooks (any endpoint)
    - Slack webhooks
    - Discord webhooks
"""

import json
import logging
import os
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from scrapy import signals
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    url: str
    enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    format: str = "json"  # json, slack, discord


class WebhookExtension:
    """
    Scrapy extension for sending webhooks on new articles.
    
    Configuration (settings or environment):
        WEBHOOK_ENABLED: Enable webhooks (default: False)
        WEBHOOK_URL: Primary webhook URL
        WEBHOOK_FORMAT: json, slack, or discord
        WEBHOOK_BATCH_SIZE: Articles per batch (default: 10)
        
        Multiple webhooks via WEBHOOKS setting:
        WEBHOOKS = [
            {'url': 'https://...', 'format': 'slack'},
            {'url': 'https://...', 'format': 'discord'},
        ]
    """
    
    def __init__(self, webhooks: List[WebhookConfig], batch_size: int = 10):
        self.webhooks = webhooks
        self.batch_size = batch_size
        self.article_buffer: List[Dict] = []
        self.stats = {
            'webhooks_sent': 0,
            'webhooks_failed': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('WEBHOOK_ENABLED', False)
        if not enabled:
            raise NotConfigured("Webhook extension disabled")
        
        webhooks = []
        
        # Single webhook from settings
        url = crawler.settings.get('WEBHOOK_URL') or os.getenv('WEBHOOK_URL')
        if url:
            webhooks.append(WebhookConfig(
                url=url,
                format=crawler.settings.get('WEBHOOK_FORMAT', 'json'),
            ))
        
        # Multiple webhooks from settings
        webhook_list = crawler.settings.getlist('WEBHOOKS', [])
        for wh in webhook_list:
            if isinstance(wh, dict) and wh.get('url'):
                webhooks.append(WebhookConfig(
                    url=wh['url'],
                    format=wh.get('format', 'json'),
                    headers=wh.get('headers', {}),
                ))
        
        if not webhooks:
            raise NotConfigured("No webhook URLs configured")
        
        extension = cls(
            webhooks=webhooks,
            batch_size=crawler.settings.getint('WEBHOOK_BATCH_SIZE', 10),
        )
        
        crawler.signals.connect(extension.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        
        return extension
    
    def item_scraped(self, item, response, spider):
        """Buffer scraped articles and send when batch is full."""
        self.article_buffer.append({
            'url': item.get('url'),
            'headline': item.get('headline'),
            'paper_name': item.get('paper_name'),
            'category': item.get('category'),
            'author': item.get('author'),
            'publication_date': item.get('publication_date'),
        })
        
        if len(self.article_buffer) >= self.batch_size:
            self._send_batch(spider)
    
    def spider_closed(self, spider, reason):
        """Send remaining articles on spider close."""
        if self.article_buffer:
            self._send_batch(spider)
        
        spider.logger.info(
            f"Webhook stats: {self.stats['webhooks_sent']} sent, "
            f"{self.stats['webhooks_failed']} failed"
        )
    
    def _send_batch(self, spider):
        """Send batch of articles to all webhooks."""
        articles = self.article_buffer.copy()
        self.article_buffer.clear()
        
        for webhook in self.webhooks:
            if not webhook.enabled:
                continue
            
            try:
                payload = self._format_payload(articles, webhook.format, spider)
                self._send_webhook(webhook, payload)
                self.stats['webhooks_sent'] += 1
                spider.logger.debug(f"Webhook sent to {webhook.url[:50]}...")
            except Exception as e:
                self.stats['webhooks_failed'] += 1
                spider.logger.error(f"Webhook failed: {e}")
    
    def _format_payload(self, articles: List[Dict], format: str, spider) -> Dict:
        """Format payload based on webhook type."""
        if format == 'slack':
            return self._format_slack(articles, spider)
        elif format == 'discord':
            return self._format_discord(articles, spider)
        else:
            return self._format_json(articles, spider)
    
    def _format_json(self, articles: List[Dict], spider) -> Dict:
        """Standard JSON format."""
        return {
            'event': 'articles_scraped',
            'spider': spider.name,
            'count': len(articles),
            'timestamp': datetime.now().isoformat(),
            'articles': articles,
        }
    
    def _format_slack(self, articles: List[Dict], spider) -> Dict:
        """Slack message format."""
        article_lines = []
        for a in articles[:5]:  # Limit to 5 in Slack
            article_lines.append(f"• <{a['url']}|{a['headline'][:50]}...>")
        
        return {
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': f"🗞️ {len(articles)} New Articles from {spider.name}"
                    }
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': '\n'.join(article_lines)
                    }
                }
            ]
        }
    
    def _format_discord(self, articles: List[Dict], spider) -> Dict:
        """Discord embed format."""
        embeds = []
        for a in articles[:5]:  # Limit to 5 embeds
            embeds.append({
                'title': a['headline'][:256],
                'url': a['url'],
                'color': 3447003,  # Blue
                'footer': {'text': a.get('paper_name', spider.name)},
            })
        
        return {
            'content': f"🗞️ **{len(articles)} New Articles Scraped**",
            'embeds': embeds,
        }
    
    def _send_webhook(self, webhook: WebhookConfig, payload: Dict):
        """Send HTTP POST to webhook URL."""
        data = json.dumps(payload).encode('utf-8')
        
        headers = {
            'Content-Type': 'application/json',
            **webhook.headers,
        }
        
        req = urllib.request.Request(
            webhook.url,
            data=data,
            headers=headers,
            method='POST',
        )
        
        urllib.request.urlopen(req, timeout=30)
