"""
Dynamic Configuration System
=============================
Self-healing spider configuration with selector database.

Features:
    - Store working CSS selectors per newspaper
    - Track selector success/failure rates
    - Auto-fallback to backup selectors
    - Configurable via JSON/Database

Usage:
    from BDNewsPaper.dynamic_config import SelectorConfig
    
    config = SelectorConfig.load('prothomalo')
    headline_selector = config.get_selector('headline')
"""

import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SelectorEntry:
    """A single selector with metadata."""
    selector: str
    selector_type: str = "css"  # css, xpath, json
    priority: int = 1  # Higher = preferred
    success_count: int = 0
    failure_count: int = 0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def record_success(self):
        self.success_count += 1
        self.last_success = datetime.now().isoformat()
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.now().isoformat()


@dataclass
class SelectorConfig:
    """Configuration for a single newspaper's selectors."""
    paper_name: str
    selectors: Dict[str, List[SelectorEntry]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_selector(self, field_name: str) -> Optional[str]:
        """Get the best working selector for a field."""
        entries = self.selectors.get(field_name, [])
        if not entries:
            return None
        
        # Sort by priority and success rate
        sorted_entries = sorted(
            entries,
            key=lambda e: (e.priority, e.success_rate),
            reverse=True
        )
        
        return sorted_entries[0].selector
    
    def get_all_selectors(self, field_name: str) -> List[str]:
        """Get all selectors for fallback iteration."""
        entries = self.selectors.get(field_name, [])
        sorted_entries = sorted(
            entries,
            key=lambda e: (e.priority, e.success_rate),
            reverse=True
        )
        return [e.selector for e in sorted_entries]
    
    def record_success(self, field_name: str, selector: str):
        """Record successful use of a selector."""
        entries = self.selectors.get(field_name, [])
        for entry in entries:
            if entry.selector == selector:
                entry.record_success()
                break
    
    def record_failure(self, field_name: str, selector: str):
        """Record failed use of a selector."""
        entries = self.selectors.get(field_name, [])
        for entry in entries:
            if entry.selector == selector:
                entry.record_failure()
                break
    
    def add_selector(self, field_name: str, selector: str, priority: int = 1):
        """Add a new selector for a field."""
        if field_name not in self.selectors:
            self.selectors[field_name] = []
        
        # Check if already exists
        for entry in self.selectors[field_name]:
            if entry.selector == selector:
                return
        
        self.selectors[field_name].append(SelectorEntry(
            selector=selector,
            priority=priority,
        ))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'paper_name': self.paper_name,
            'selectors': {
                k: [asdict(e) for e in v]
                for k, v in self.selectors.items()
            },
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SelectorConfig':
        """Create from dictionary."""
        config = cls(paper_name=data['paper_name'])
        config.metadata = data.get('metadata', {})
        
        for field_name, entries in data.get('selectors', {}).items():
            config.selectors[field_name] = [
                SelectorEntry(**e) for e in entries
            ]
        
        return config


class ConfigStore:
    """
    Persistent storage for selector configurations.
    
    Supports both JSON file and SQLite database backends.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or "config/selectors")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, SelectorConfig] = {}
    
    def load(self, paper_name: str) -> SelectorConfig:
        """Load configuration for a newspaper."""
        if paper_name in self._cache:
            return self._cache[paper_name]
        
        config_file = self.storage_path / f"{paper_name}.json"
        
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                config = SelectorConfig.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load config for {paper_name}: {e}")
                config = SelectorConfig(paper_name=paper_name)
        else:
            config = SelectorConfig(paper_name=paper_name)
        
        self._cache[paper_name] = config
        return config
    
    def save(self, config: SelectorConfig):
        """Save configuration to storage."""
        config_file = self.storage_path / f"{config.paper_name}.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            self._cache[config.paper_name] = config
        except Exception as e:
            logger.error(f"Failed to save config for {config.paper_name}: {e}")
    
    def list_papers(self) -> List[str]:
        """List all configured papers."""
        files = self.storage_path.glob("*.json")
        return [f.stem for f in files]


# Default selectors for common newspapers
DEFAULT_SELECTORS = {
    'prothomalo': {
        'headline': ['h1.story-title', 'h1[itemprop="headline"]', 'h1'],
        'body': ['.story-content p', 'article p', '.story-element p'],
        'author': ['.author-name', '.contributor-name', '[rel="author"]'],
        'date': ['time[datetime]', '.published-time', '.story-time'],
    },
    'thedailystar': {
        'headline': ['h1.article-title', 'h1.title', 'h1'],
        'body': ['.article-body p', '.content p', 'article p'],
        'author': ['.author', '.reporter-name'],
        'date': ['.published-date', 'time'],
    },
    'dailysun': {
        'headline': ['h1.news-title', 'h1'],
        'body': ['.news-content p', '.article-body p'],
        'author': ['.reporter'],
        'date': ['.date', 'time'],
    },
}


def initialize_default_configs(store: ConfigStore = None):
    """Initialize default selector configurations."""
    if store is None:
        store = ConfigStore()
    
    for paper_name, fields in DEFAULT_SELECTORS.items():
        config = store.load(paper_name)
        
        for field_name, selectors in fields.items():
            for priority, selector in enumerate(selectors, 1):
                config.add_selector(field_name, selector, priority=len(selectors) - priority + 1)
        
        store.save(config)
        logger.info(f"Initialized default config for {paper_name}")


# Convenience singleton
_default_store: Optional[ConfigStore] = None


def get_store() -> ConfigStore:
    """Get the default configuration store."""
    global _default_store
    if _default_store is None:
        _default_store = ConfigStore()
    return _default_store


def get_config(paper_name: str) -> SelectorConfig:
    """Get configuration for a newspaper."""
    return get_store().load(paper_name)
