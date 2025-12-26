"""
Distributed Spider Infrastructure
==================================
Celery-based distributed task queue for spider execution.

Features:
    - Celery task definitions for spider runs
    - Redis/RabbitMQ broker support
    - Priority-based scheduling
    - Result backend with status tracking
    - Periodic task scheduling (beat)
    - Worker scaling support

Requirements:
    pip install celery[redis] redis

Usage:
    # Start worker
    celery -A BDNewsPaper.distributed worker -l INFO
    
    # Start beat scheduler
    celery -A BDNewsPaper.distributed beat -l INFO
    
    # Dispatch spider task
    from BDNewsPaper.distributed import run_spider
    result = run_spider.delay('prothomalo', max_items=100)

Settings (via environment or settings.py):
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
"""

import os
import json
import logging
from datetime import timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Check Celery availability
try:
    from celery import Celery, Task
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    Task = object
    crontab = None


# =============================================================================
# CELERY APP CONFIGURATION
# =============================================================================

def create_celery_app(
    broker_url: str = None,
    result_backend: str = None,
) -> Optional['Celery']:
    """
    Create and configure Celery application.
    
    Args:
        broker_url: Redis/RabbitMQ URL
        result_backend: Result storage URL
    """
    if not CELERY_AVAILABLE:
        logger.warning("Celery not available. Install with: pip install celery[redis]")
        return None
    
    broker = broker_url or os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    backend = result_backend or os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    
    app = Celery(
        'bdnews_scraper',
        broker=broker,
        backend=backend,
    )
    
    # Configuration
    app.conf.update(
        # Task settings
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Dhaka',
        enable_utc=True,
        
        # Task tracking
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max per task
        task_soft_time_limit=3000,  # Soft limit 50 min
        
        # Result settings
        result_expires=86400,  # Results expire after 24h
        
        # Worker settings
        worker_prefetch_multiplier=1,  # One task at a time per worker
        worker_concurrency=4,
        
        # Task routing
        task_routes={
            'BDNewsPaper.distributed.run_spider': {'queue': 'spiders'},
            'BDNewsPaper.distributed.run_spider_batch': {'queue': 'spiders'},
            'BDNewsPaper.distributed.health_check': {'queue': 'monitoring'},
        },
        
        # Priority queues
        task_default_queue='default',
        task_queues={
            'spiders': {'exchange': 'spiders', 'routing_key': 'spider.#'},
            'monitoring': {'exchange': 'monitoring', 'routing_key': 'monitor.#'},
            'default': {'exchange': 'default', 'routing_key': 'default'},
        },
    )
    
    return app


# Create default app
celery_app = create_celery_app() if CELERY_AVAILABLE else None


# =============================================================================
# TASK RESULT MODELS
# =============================================================================

@dataclass
class SpiderResult:
    """Result from a spider run."""
    spider_name: str
    items_scraped: int
    items_dropped: int
    requests_made: int
    errors: int
    duration_seconds: float
    status: str  # 'success', 'failed', 'timeout'
    error_message: str = ''
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BatchResult:
    """Result from a batch spider run."""
    total_spiders: int
    successful: int
    failed: int
    total_items: int
    results: List[SpiderResult]
    
    def to_dict(self) -> Dict:
        return {
            'total_spiders': self.total_spiders,
            'successful': self.successful,
            'failed': self.failed,
            'total_items': self.total_items,
            'results': [r.to_dict() for r in self.results],
        }


# =============================================================================
# SPIDER EXECUTION ENGINE
# =============================================================================

def execute_spider(
    spider_name: str,
    settings: Dict = None,
    max_items: int = None,
    output_file: str = None,
) -> SpiderResult:
    """
    Execute a Scrapy spider and return results.
    
    This runs in the worker process.
    """
    import time
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    
    start_time = time.time()
    
    try:
        # Get Scrapy settings
        scrapy_settings = get_project_settings()
        
        # Override with custom settings
        if settings:
            for key, value in settings.items():
                scrapy_settings.set(key, value)
        
        # Set item limit
        if max_items:
            scrapy_settings.set('CLOSESPIDER_ITEMCOUNT', max_items)
        
        # Set output file
        if output_file:
            scrapy_settings.set('FEEDS', {
                output_file: {'format': 'jsonlines'},
            })
        
        # Create crawler
        process = CrawlerProcess(scrapy_settings)
        
        # Track stats
        stats_holder = {'stats': {}}
        
        def stats_callback(stats):
            stats_holder['stats'] = stats
        
        # Run spider
        crawler = process.create_crawler(spider_name)
        process.crawl(crawler)
        process.start(stop_after_crawl=True)
        
        # Get stats
        stats = crawler.stats.get_stats()
        
        duration = time.time() - start_time
        
        return SpiderResult(
            spider_name=spider_name,
            items_scraped=stats.get('item_scraped_count', 0),
            items_dropped=stats.get('item_dropped_count', 0),
            requests_made=stats.get('downloader/request_count', 0),
            errors=stats.get('log_count/ERROR', 0),
            duration_seconds=duration,
            status='success',
        )
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Spider {spider_name} failed: {e}")
        
        return SpiderResult(
            spider_name=spider_name,
            items_scraped=0,
            items_dropped=0,
            requests_made=0,
            errors=1,
            duration_seconds=duration,
            status='failed',
            error_message=str(e),
        )


# =============================================================================
# CELERY TASKS
# =============================================================================

if CELERY_AVAILABLE and celery_app:
    
    @celery_app.task(bind=True, name='BDNewsPaper.distributed.run_spider')
    def run_spider(
        self,
        spider_name: str,
        max_items: int = None,
        settings: Dict = None,
    ) -> Dict:
        """
        Run a single spider as a Celery task.
        
        Args:
            spider_name: Name of spider to run
            max_items: Maximum items to scrape
            settings: Custom Scrapy settings
            
        Returns:
            SpiderResult as dictionary
        """
        logger.info(f"Starting spider: {spider_name}")
        
        self.update_state(state='RUNNING', meta={'spider': spider_name})
        
        result = execute_spider(
            spider_name,
            settings=settings,
            max_items=max_items,
        )
        
        return result.to_dict()
    
    
    @celery_app.task(bind=True, name='BDNewsPaper.distributed.run_spider_batch')
    def run_spider_batch(
        self,
        spider_names: List[str],
        max_items_per_spider: int = None,
        settings: Dict = None,
    ) -> Dict:
        """
        Run multiple spiders sequentially.
        
        Args:
            spider_names: List of spider names
            max_items_per_spider: Max items per spider
            settings: Shared settings
            
        Returns:
            BatchResult as dictionary
        """
        results = []
        total_items = 0
        
        for i, spider_name in enumerate(spider_names):
            self.update_state(
                state='RUNNING',
                meta={
                    'current_spider': spider_name,
                    'progress': f"{i + 1}/{len(spider_names)}",
                }
            )
            
            result = execute_spider(
                spider_name,
                settings=settings,
                max_items=max_items_per_spider,
            )
            
            results.append(result)
            total_items += result.items_scraped
        
        successful = sum(1 for r in results if r.status == 'success')
        
        return BatchResult(
            total_spiders=len(spider_names),
            successful=successful,
            failed=len(spider_names) - successful,
            total_items=total_items,
            results=results,
        ).to_dict()
    
    
    @celery_app.task(name='BDNewsPaper.distributed.health_check')
    def health_check() -> Dict:
        """
        Check system health and return status.
        """
        import psutil
        
        return {
            'status': 'healthy',
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        }
    
    
    # =========================================================================
    # PERIODIC TASK SCHEDULE (Celery Beat)
    # =========================================================================
    
    celery_app.conf.beat_schedule = {
        # Daily full scrape at 2 AM Bangladesh time
        'daily-full-scrape': {
            'task': 'BDNewsPaper.distributed.run_spider_batch',
            'schedule': crontab(hour=2, minute=0),
            'args': [
                [
                    'prothomalo', 'thedailystar', 'bdnews24',
                    'dailysun', 'banglanews24', 'jugantor',
                ],
            ],
            'kwargs': {'max_items_per_spider': 100},
        },
        
        # Hourly health check
        'hourly-health-check': {
            'task': 'BDNewsPaper.distributed.health_check',
            'schedule': crontab(minute=0),
        },
        
        # Every 6 hours - top newspapers
        'frequent-scrape': {
            'task': 'BDNewsPaper.distributed.run_spider_batch',
            'schedule': crontab(hour='*/6', minute=15),
            'args': [['prothomalo', 'thedailystar']],
            'kwargs': {'max_items_per_spider': 50},
        },
    }


# =============================================================================
# CONVENIENCE FUNCTIONS (for non-Celery usage)
# =============================================================================

def dispatch_spider(spider_name: str, **kwargs) -> Optional[str]:
    """
    Dispatch a spider task and return task ID.
    
    Returns None if Celery not available.
    """
    if not CELERY_AVAILABLE or not celery_app:
        logger.warning("Celery not available, running synchronously")
        result = execute_spider(spider_name, **kwargs)
        return None
    
    task = run_spider.delay(spider_name, **kwargs)
    return task.id


def dispatch_batch(spider_names: List[str], **kwargs) -> Optional[str]:
    """
    Dispatch a batch spider task and return task ID.
    """
    if not CELERY_AVAILABLE or not celery_app:
        logger.warning("Celery not available")
        return None
    
    task = run_spider_batch.delay(spider_names, **kwargs)
    return task.id


def get_task_status(task_id: str) -> Dict:
    """
    Get status of a task by ID.
    """
    if not CELERY_AVAILABLE or not celery_app:
        return {'status': 'unavailable'}
    
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None,
        'info': result.info if result.state == 'RUNNING' else None,
    }


# =============================================================================
# DOCKER COMPOSE TEMPLATE
# =============================================================================

DOCKER_COMPOSE_TEMPLATE = """
# docker-compose.yml for distributed scraping
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build: .
    command: celery -A BDNewsPaper.distributed worker -l INFO -Q spiders,default
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - redis
    deploy:
      replicas: 4  # Scale workers

  beat:
    build: .
    command: celery -A BDNewsPaper.distributed beat -l INFO
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - redis

  flower:
    image: mher/flower
    command: celery flower --broker=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  redis_data:
"""


def generate_docker_compose(output_path: str = 'docker-compose.distributed.yml'):
    """Generate Docker Compose file for distributed setup."""
    with open(output_path, 'w') as f:
        f.write(DOCKER_COMPOSE_TEMPLATE.strip())
    logger.info(f"Generated {output_path}")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'celery_app',
    'run_spider',
    'run_spider_batch',
    'health_check',
    'dispatch_spider',
    'dispatch_batch',
    'get_task_status',
    'execute_spider',
    'SpiderResult',
    'BatchResult',
    'generate_docker_compose',
    'CELERY_AVAILABLE',
]
