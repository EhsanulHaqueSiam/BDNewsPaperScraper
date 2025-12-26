"""
Redis Caching for API
======================
Add caching layer to API for faster response times.

Features:
    - Cache API responses
    - Configurable TTL per endpoint
    - Cache invalidation on data update
    - Statistics tracking

Usage:
    Set REDIS_URL in environment
    Import and use with FastAPI dependency injection
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Any, Callable
from functools import wraps

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Install redis: pip install redis")


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Default TTLs in seconds
CACHE_TTLS = {
    "articles_list": 300,      # 5 minutes
    "article_detail": 3600,    # 1 hour
    "stats": 600,              # 10 minutes
    "search": 300,             # 5 minutes
    "papers": 3600,            # 1 hour
    "categories": 3600,        # 1 hour
}


class RedisCache:
    """Redis caching wrapper."""
    
    def __init__(self, url: str = None):
        self.url = url or REDIS_URL
        self.client = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            return
        
        try:
            self.client = redis.from_url(
                self.url,
                decode_responses=True,
                socket_timeout=5
            )
            self.client.ping()
            print(f"✅ Redis connected: {self.url}")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            self.client = None
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self.client is not None
    
    def _make_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from prefix and params."""
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"bdnews:{prefix}:{param_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                self.stats["hits"] += 1
                return json.loads(value)
            self.stats["misses"] += 1
            return None
        except Exception as e:
            self.stats["errors"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        if not self.is_available:
            return False
        
        try:
            self.client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def delete(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self.is_available:
            return 0
        
        try:
            keys = self.client.keys(f"bdnews:{pattern}*")
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            return 0
    
    def invalidate_all(self) -> int:
        """Invalidate all cache entries."""
        return self.delete("")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = self.stats.copy()
        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"]) * 100
            if (stats["hits"] + stats["misses"]) > 0 else 0
        )
        stats["available"] = self.is_available
        return stats


# Global cache instance
cache = RedisCache()


def cached(prefix: str, ttl: int = None):
    """
    Decorator for caching function results.
    
    Usage:
        @cached("articles_list", ttl=300)
        async def list_articles(page: int, per_page: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            cache_key = cache._make_key(prefix, kwargs)
            
            # Try cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_ttl = ttl or CACHE_TTLS.get(prefix, 300)
            cache.set(cache_key, result, cache_ttl)
            
            return result
        
        return wrapper
    return decorator


# =============================================================================
# FastAPI Integration
# =============================================================================

def get_cache() -> RedisCache:
    """FastAPI dependency for cache."""
    return cache


# Example API integration:
"""
from fastapi import FastAPI, Depends
from redis_cache import cached, get_cache, RedisCache

app = FastAPI()

@app.get("/articles")
@cached("articles_list", ttl=300)
async def list_articles(page: int = 1, per_page: int = 20):
    # Your existing code
    ...

@app.get("/cache/stats")
async def cache_stats(cache: RedisCache = Depends(get_cache)):
    return cache.get_stats()

@app.post("/cache/invalidate")
async def invalidate_cache(cache: RedisCache = Depends(get_cache)):
    count = cache.invalidate_all()
    return {"invalidated": count}
"""
