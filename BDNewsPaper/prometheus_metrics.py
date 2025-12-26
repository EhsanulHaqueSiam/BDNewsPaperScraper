"""
Prometheus Metrics Extension
============================
Exports Scrapy spider metrics in Prometheus format.

Features:
    - Items scraped per spider
    - Requests/responses per domain
    - Error counts by type
    - Response time histograms
    - Optional Pushgateway integration

Usage:
    # Add to settings.py
    EXTENSIONS = {
        'BDNewsPaper.prometheus_metrics.PrometheusMetricsExtension': 500,
    }
    
    # Configure
    PROMETHEUS_ENABLED = True
    PROMETHEUS_PORT = 9100  # Metrics endpoint port
    PROMETHEUS_PUSHGATEWAY = 'http://localhost:9091'  # Optional

Then access metrics at: http://localhost:9100/metrics
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Optional
from threading import Thread

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, 
        start_http_server, push_to_gateway, CollectorRegistry, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from scrapy import signals
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


class PrometheusMetricsExtension:
    """
    Scrapy extension for Prometheus metrics export.
    
    Exposes metrics endpoint and optionally pushes to Pushgateway.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        port: int = 9100,
        pushgateway_url: Optional[str] = None,
        push_interval: int = 60,
        job_name: str = 'bdnews_scraper',
    ):
        if not PROMETHEUS_AVAILABLE:
            raise NotConfigured("prometheus_client not installed. Run: pip install prometheus-client")
        
        self.enabled = enabled
        self.port = port
        self.pushgateway_url = pushgateway_url
        self.push_interval = push_interval
        self.job_name = job_name
        
        self.registry = REGISTRY
        self._setup_metrics()
        
        self.server_started = False
        self.last_push = 0
    
    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        # Counters
        self.items_scraped = Counter(
            'scrapy_items_scraped_total',
            'Total items scraped',
            ['spider', 'paper']
        )
        
        self.items_dropped = Counter(
            'scrapy_items_dropped_total',
            'Total items dropped',
            ['spider', 'reason']
        )
        
        self.requests_total = Counter(
            'scrapy_requests_total',
            'Total requests made',
            ['spider', 'domain']
        )
        
        self.responses_total = Counter(
            'scrapy_responses_total',
            'Total responses received',
            ['spider', 'status_code']
        )
        
        self.errors_total = Counter(
            'scrapy_errors_total',
            'Total errors encountered',
            ['spider', 'error_type']
        )
        
        # Gauges
        self.spider_running = Gauge(
            'scrapy_spider_running',
            'Spider currently running',
            ['spider']
        )
        
        self.pending_requests = Gauge(
            'scrapy_pending_requests',
            'Pending requests in scheduler',
            ['spider']
        )
        
        # Histograms
        self.response_time = Histogram(
            'scrapy_response_time_seconds',
            'Response time in seconds',
            ['spider', 'domain'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.item_size = Histogram(
            'scrapy_item_size_bytes',
            'Item size in bytes',
            ['spider'],
            buckets=[100, 500, 1000, 5000, 10000, 50000]
        )
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('PROMETHEUS_ENABLED', False)
        if not enabled:
            raise NotConfigured("Prometheus metrics disabled")
        
        ext = cls(
            enabled=True,
            port=crawler.settings.getint('PROMETHEUS_PORT', 9100),
            pushgateway_url=crawler.settings.get('PROMETHEUS_PUSHGATEWAY'),
            push_interval=crawler.settings.getint('PROMETHEUS_PUSH_INTERVAL', 60),
            job_name=crawler.settings.get('PROMETHEUS_JOB_NAME', 'bdnews_scraper'),
        )
        
        # Connect signals
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(ext.request_scheduled, signal=signals.request_scheduled)
        crawler.signals.connect(ext.response_received, signal=signals.response_received)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        
        return ext
    
    def _start_server(self):
        """Start metrics HTTP server."""
        if not self.server_started:
            try:
                start_http_server(self.port)
                self.server_started = True
                logger.info(f"Prometheus metrics available at http://localhost:{self.port}/metrics")
            except Exception as e:
                logger.warning(f"Could not start Prometheus server: {e}")
    
    def _push_metrics(self):
        """Push metrics to Pushgateway if configured."""
        if not self.pushgateway_url:
            return
        
        now = time.time()
        if now - self.last_push < self.push_interval:
            return
        
        try:
            push_to_gateway(self.pushgateway_url, job=self.job_name, registry=self.registry)
            self.last_push = now
            logger.debug(f"Pushed metrics to {self.pushgateway_url}")
        except Exception as e:
            logger.warning(f"Failed to push metrics: {e}")
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def spider_opened(self, spider):
        """Track spider start."""
        self._start_server()
        self.spider_running.labels(spider=spider.name).set(1)
        logger.info(f"Prometheus tracking spider: {spider.name}")
    
    def spider_closed(self, spider, reason):
        """Track spider stop."""
        self.spider_running.labels(spider=spider.name).set(0)
        self._push_metrics()  # Final push
    
    def item_scraped(self, item, spider):
        """Track scraped item."""
        paper = item.get('paper_name', 'unknown')
        self.items_scraped.labels(spider=spider.name, paper=paper).inc()
        
        # Track item size
        try:
            import json
            size = len(json.dumps(dict(item)))
            self.item_size.labels(spider=spider.name).observe(size)
        except:
            pass
        
        self._push_metrics()
    
    def item_dropped(self, item, spider, exception):
        """Track dropped item."""
        reason = type(exception).__name__
        self.items_dropped.labels(spider=spider.name, reason=reason).inc()
    
    def request_scheduled(self, request, spider):
        """Track scheduled request."""
        domain = self._get_domain(request.url)
        self.requests_total.labels(spider=spider.name, domain=domain).inc()
    
    def response_received(self, response, request, spider):
        """Track response."""
        status = str(response.status)
        self.responses_total.labels(spider=spider.name, status_code=status).inc()
        
        # Track response time
        start_time = request.meta.get('_start_time')
        if start_time:
            elapsed = time.time() - start_time
            domain = self._get_domain(request.url)
            self.response_time.labels(spider=spider.name, domain=domain).observe(elapsed)
    
    def spider_error(self, failure, response, spider):
        """Track errors."""
        error_type = failure.type.__name__ if failure.type else 'Unknown'
        self.errors_total.labels(spider=spider.name, error_type=error_type).inc()
