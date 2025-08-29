import random
import time
import logging
from collections import defaultdict
from typing import Optional, Union, Dict, List
from datetime import datetime, timedelta

import scrapy
from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import NotConfigured, IgnoreRequest
from scrapy.utils.response import response_status_message
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from itemadapter import is_item, ItemAdapter


class BdnewspaperSpiderMiddleware:
    def __init__(self, stats=None):
        self.stats = stats
        self.spider_stats: Dict[str, Dict] = defaultdict(lambda: {
            'items_scraped': 0,
            'items_dropped': 0,
            'requests_processed': 0,
            'exceptions_caught': 0,
            'start_time': None
        })

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(stats=crawler.stats)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def process_spider_input(self, response, spider):
        self.spider_stats[spider.name]['requests_processed'] += 1
        
        if response.status >= 400:
            spider.logger.warning(
                f"Processing response with status {response.status} from {response.url}"
            )
        
        return None

    def process_spider_output(self, response, result, spider):
        for item in result:
            if is_item(item):
                self.spider_stats[spider.name]['items_scraped'] += 1
                spider.logger.debug(f"Item scraped from {response.url}")
            elif isinstance(item, Request):
                spider.logger.debug(f"Request generated: {item.url}")
            
            yield item

    def process_spider_exception(self, response, exception, spider):
        self.spider_stats[spider.name]['exceptions_caught'] += 1
        spider.logger.error(
            f"Exception in spider {spider.name} for {response.url}: {exception}"
        )
        
        if self.stats:
            self.stats.inc_value(f'spider_exceptions/{spider.name}')
        
        return None

    def process_start_requests(self, start_requests, spider):
        spider.logger.info(f"Processing start requests for {spider.name}")
        
        for request in start_requests:
            request.meta['spider_start_time'] = time.time()
            yield request

    def spider_opened(self, spider):
        self.spider_stats[spider.name]['start_time'] = datetime.now()
        spider.logger.info(f"Spider {spider.name} opened with enhanced middleware")

    def spider_closed(self, spider, reason):
        stats = self.spider_stats[spider.name]
        runtime = datetime.now() - stats['start_time'] if stats['start_time'] else timedelta(0)
        
        spider.logger.info(f"=== Spider {spider.name} Statistics ===")
        spider.logger.info(f"Runtime: {runtime}")
        spider.logger.info(f"Items scraped: {stats['items_scraped']}")
        spider.logger.info(f"Items dropped: {stats['items_dropped']}")
        spider.logger.info(f"Requests processed: {stats['requests_processed']}")
        spider.logger.info(f"Exceptions caught: {stats['exceptions_caught']}")
        spider.logger.info(f"Closed reason: {reason}")


class UserAgentMiddleware:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
        ]

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        spider.logger.debug(f"Set User-Agent for {request.url}: {ua[:50]}...")
        return None


class SmartRetryMiddleware(RetryMiddleware):
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429]))
        self.backoff_factor = settings.getfloat('RETRY_BACKOFF_FACTOR', 2.0)
        self.max_delay = settings.getfloat('RETRY_MAX_DELAY', 60.0)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            spider.logger.warning(f"Retrying {request.url} due to {response.status}: {reason}")
            return self._retry_with_backoff(request, reason, spider) or response
        
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, (TimeoutError, ConnectionError)):
            reason = f"Exception: {exception.__class__.__name__}"
            spider.logger.warning(f"Retrying {request.url} due to exception: {reason}")
            return self._retry_with_backoff(request, reason, spider)
        
        return None

    def _retry_with_backoff(self, request, reason, spider):
        retry_times = request.meta.get('retry_times', 0) + 1
        
        if retry_times <= self.max_retry_times:
            delay = min(self.backoff_factor ** retry_times, self.max_delay)
            
            spider.logger.info(f"Retry {retry_times}/{self.max_retry_times} for {request.url} in {delay:.1f}s")
            
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retry_times
            retryreq.dont_filter = True
            retryreq.meta['download_delay'] = delay
            
            return retryreq
        else:
            spider.logger.error(f"Gave up retrying {request.url} after {self.max_retry_times} attempts")
            return None


class StatisticsMiddleware:
    def __init__(self):
        self.stats: Dict[str, Dict] = defaultdict(lambda: {
            'requests_total': 0,
            'responses_received': 0,
            'items_scraped': 0,
            'bytes_downloaded': 0,
            'response_times': [],
            'status_codes': defaultdict(int),
            'domains': defaultdict(int),
            'start_time': time.time()
        })

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        self.stats[spider.name]['requests_total'] += 1
        request.meta['request_start_time'] = time.time()
        
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc
        self.stats[spider.name]['domains'][domain] += 1
        
        return None

    def process_response(self, request, response, spider):
        stats = self.stats[spider.name]
        stats['responses_received'] += 1
        stats['status_codes'][response.status] += 1
        
        if hasattr(response, 'body'):
            stats['bytes_downloaded'] += len(response.body)
        
        if 'request_start_time' in request.meta:
            response_time = time.time() - request.meta['request_start_time']
            stats['response_times'].append(response_time)
        
        return response

    def spider_closed(self, spider, reason):
        stats = self.stats[spider.name]
        runtime = time.time() - stats['start_time']
        
        avg_response_time = 0
        if stats['response_times']:
            avg_response_time = sum(stats['response_times']) / len(stats['response_times'])
        
        spider.logger.info(f"=== Detailed Statistics for {spider.name} ===")
        spider.logger.info(f"Runtime: {runtime:.1f}s")
        spider.logger.info(f"Requests made: {stats['requests_total']}")
        spider.logger.info(f"Responses received: {stats['responses_received']}")
        spider.logger.info(f"Bytes downloaded: {stats['bytes_downloaded']:,}")
        spider.logger.info(f"Average response time: {avg_response_time:.3f}s")
        
        spider.logger.info("Status codes:")
        for code, count in sorted(stats['status_codes'].items()):
            spider.logger.info(f"  {code}: {count}")
        
        spider.logger.info("Top domains:")
        for domain, count in sorted(stats['domains'].items(), key=lambda x: x[1], reverse=True)[:5]:
            spider.logger.info(f"  {domain}: {count}")


class RateLimitMiddleware:
    def __init__(self, delay=1.0, randomize=True):
        self.delay = delay
        self.randomize = randomize
        self.last_request_time = defaultdict(float)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        delay = settings.getfloat('RATELIMIT_DELAY', 1.0)
        randomize = settings.getbool('RATELIMIT_RANDOMIZE', True)
        return cls(delay=delay, randomize=randomize)

    def process_request(self, request, spider):
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc
        
        now = time.time()
        last_time = self.last_request_time[domain]
        
        if last_time > 0:
            elapsed = now - last_time
            delay = self.delay
            
            if self.randomize:
                delay *= random.uniform(0.5, 1.5)
            
            if elapsed < delay:
                sleep_time = delay - elapsed
                spider.logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()
        return None


class BdnewspaperDownloaderMiddleware:
    def __init__(self, stats=None):
        self.stats = stats
        self.failed_requests = defaultdict(int)

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(stats=crawler.stats)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request, spider):
        request.headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request.headers.setdefault('Accept-Language', 'en-US,en;q=0.5')
        request.headers.setdefault('Accept-Encoding', 'gzip, deflate')
        request.headers.setdefault('DNT', '1')
        request.headers.setdefault('Connection', 'keep-alive')
        request.headers.setdefault('Upgrade-Insecure-Requests', '1')
        
        spider.logger.debug(f"Processing request to {request.url}")
        return None

    def process_response(self, request, response, spider):
        if response.status == 429:
            spider.logger.warning(f"Rate limited on {request.url}")
            self.failed_requests[spider.name] += 1
            
            if self.stats:
                self.stats.inc_value('downloader/response_status_count/429')
        
        elif response.status >= 400:
            spider.logger.warning(f"HTTP {response.status} for {request.url}")
            self.failed_requests[spider.name] += 1
        
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f"Download exception for {request.url}: {exception}")
        self.failed_requests[spider.name] += 1
        
        if self.stats:
            self.stats.inc_value(f'downloader/exception_type_count/{exception.__class__.__name__}')
        
        return None

    def spider_opened(self, spider):
        spider.logger.info(f"Enhanced downloader middleware activated for {spider.name}")


class BdnewspaperRetryMiddleware(SmartRetryMiddleware):
    pass