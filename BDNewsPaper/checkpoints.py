"""
Checkpoint Management Module
============================
Provides checkpointing functionality for spider state persistence and recovery.

Features:
    - Save progress periodically
    - Resume scraping after crashes
    - Track processed URLs per spider
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set, Any
import logging

from scrapy import signals
from scrapy.exceptions import NotConfigured


logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoint files for spider state persistence.
    
    Checkpoint file format:
    {
        "spider_name": "prothomalo",
        "created_at": "2024-12-26T04:00:00",
        "updated_at": "2024-12-26T04:30:00",
        "processed_urls": ["url1", "url2", ...],
        "state": {
            "current_page": 5,
            "current_category": "bangladesh",
            "items_scraped": 150
        }
    }
    """
    
    def __init__(self, checkpoint_dir: str = '.checkpoints'):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def _get_checkpoint_path(self, spider_name: str) -> Path:
        """Get checkpoint file path for a spider."""
        return self.checkpoint_dir / f"{spider_name}_checkpoint.json"
    
    def save_checkpoint(self, spider_name: str, processed_urls: Set[str],
                        state: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save checkpoint for a spider.
        
        Args:
            spider_name: Name of the spider
            processed_urls: Set of processed URLs
            state: Additional spider state (e.g., current page, category)
        
        Returns:
            True if save successful, False otherwise
        """
        checkpoint_path = self._get_checkpoint_path(spider_name)
        
        # Load existing checkpoint to preserve creation time
        existing = self.load_checkpoint(spider_name)
        created_at = existing.get('created_at', datetime.now().isoformat()) if existing else datetime.now().isoformat()
        
        checkpoint_data = {
            'spider_name': spider_name,
            'created_at': created_at,
            'updated_at': datetime.now().isoformat(),
            'processed_urls': list(processed_urls),
            'processed_count': len(processed_urls),
            'state': state or {},
        }
        
        with self._lock:
            try:
                # Write to temp file first, then rename for atomicity
                temp_path = checkpoint_path.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
                temp_path.rename(checkpoint_path)
                
                logger.debug(f"Checkpoint saved for {spider_name}: {len(processed_urls)} URLs")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint for {spider_name}: {e}")
                return False
    
    def load_checkpoint(self, spider_name: str) -> Optional[Dict]:
        """
        Load checkpoint for a spider.
        
        Args:
            spider_name: Name of the spider
        
        Returns:
            Checkpoint data dict or None if not found
        """
        checkpoint_path = self._get_checkpoint_path(spider_name)
        
        if not checkpoint_path.exists():
            return None
        
        with self._lock:
            try:
                with open(checkpoint_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded checkpoint for {spider_name}: {data.get('processed_count', 0)} URLs")
                return data
                
            except Exception as e:
                logger.error(f"Failed to load checkpoint for {spider_name}: {e}")
                return None
    
    def get_processed_urls(self, spider_name: str) -> Set[str]:
        """Get set of processed URLs from checkpoint."""
        checkpoint = self.load_checkpoint(spider_name)
        if checkpoint:
            return set(checkpoint.get('processed_urls', []))
        return set()
    
    def get_state(self, spider_name: str) -> Dict[str, Any]:
        """Get spider state from checkpoint."""
        checkpoint = self.load_checkpoint(spider_name)
        if checkpoint:
            return checkpoint.get('state', {})
        return {}
    
    def clear_checkpoint(self, spider_name: str) -> bool:
        """Clear checkpoint for a spider."""
        checkpoint_path = self._get_checkpoint_path(spider_name)
        
        with self._lock:
            try:
                if checkpoint_path.exists():
                    checkpoint_path.unlink()
                    logger.info(f"Checkpoint cleared for {spider_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to clear checkpoint for {spider_name}: {e}")
                return False


class CheckpointExtension:
    """
    Scrapy extension for automatic checkpointing.
    
    Enable via settings:
        EXTENSIONS = {
            'BDNewsPaper.checkpoints.CheckpointExtension': 500,
        }
        CHECKPOINT_ENABLED = True
        CHECKPOINT_INTERVAL = 100  # Save every N items
        CHECKPOINT_DIR = '.checkpoints'
    """
    
    def __init__(self, checkpoint_interval: int = 100, checkpoint_dir: str = '.checkpoints'):
        self.checkpoint_interval = checkpoint_interval
        self.manager = CheckpointManager(checkpoint_dir)
        self.item_counts: Dict[str, int] = {}
        self.processed_urls: Dict[str, Set[str]] = {}
    
    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('CHECKPOINT_ENABLED', False):
            raise NotConfigured("Checkpoint extension is disabled")
        
        extension = cls(
            checkpoint_interval=crawler.settings.getint('CHECKPOINT_INTERVAL', 100),
            checkpoint_dir=crawler.settings.get('CHECKPOINT_DIR', '.checkpoints'),
        )
        
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(extension.item_scraped, signal=signals.item_scraped)
        
        return extension
    
    def spider_opened(self, spider):
        """Initialize checkpoint tracking for spider."""
        self.item_counts[spider.name] = 0
        self.processed_urls[spider.name] = set()
        
        # Load existing checkpoint if resuming
        if getattr(spider, 'resume', False):
            checkpoint = self.manager.load_checkpoint(spider.name)
            if checkpoint:
                self.processed_urls[spider.name] = set(checkpoint.get('processed_urls', []))
                spider.logger.info(f"Resuming from checkpoint: {len(self.processed_urls[spider.name])} URLs")
                
                # Inject state back into spider if it supports it
                state = checkpoint.get('state', {})
                if hasattr(spider, 'load_checkpoint_state'):
                    spider.load_checkpoint_state(state)
    
    def spider_closed(self, spider, reason):
        """Save final checkpoint on spider close."""
        if spider.name in self.processed_urls:
            state = {}
            if hasattr(spider, 'get_checkpoint_state'):
                state = spider.get_checkpoint_state()
            
            self.manager.save_checkpoint(
                spider.name,
                self.processed_urls[spider.name],
                state
            )
            spider.logger.info(f"Final checkpoint saved: {len(self.processed_urls[spider.name])} URLs")
    
    def item_scraped(self, item, response, spider):
        """Track scraped items and save checkpoint periodically."""
        self.item_counts[spider.name] = self.item_counts.get(spider.name, 0) + 1
        
        # Track URL
        url = item.get('url')
        if url:
            self.processed_urls[spider.name].add(url)
        
        # Save checkpoint at interval
        if self.item_counts[spider.name] % self.checkpoint_interval == 0:
            state = {}
            if hasattr(spider, 'get_checkpoint_state'):
                state = spider.get_checkpoint_state()
            
            self.manager.save_checkpoint(
                spider.name,
                self.processed_urls[spider.name],
                state
            )
            spider.logger.info(f"Checkpoint saved at {self.item_counts[spider.name]} items")
