# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

### Files

- **Spiders:** lowercase with underscores (e.g., `prothomalo.py`, `daily_sun.py`, `base_spider.py`)
- **Modules:** lowercase with underscores (e.g., `items.py`, `config.py`, `pipelines.py`, `middlewares.py`)
- **Classes:** PascalCase (e.g., `BaseNewsSpider`, `NewsArticleItem`, `ValidationPipeline`)
- **Functions:** snake_case (e.g., `clean_text`, `validate_url`, `parse_date`, `_parse_date_args`)
- **Constants:** UPPER_CASE (e.g., `DHAKA_TZ`, `DEFAULT_START_DATE`, `BASE_URL`, `CATEGORIES`)
- **Private methods/attributes:** Prefix with underscore (e.g., `_parse_date_args`, `_db_lock`, `_local`)

### Functions and Methods

- **Parsing/extraction:** Prefix with `parse_` or `extract_` (e.g., `parse_article_date`, `extract_author`, `extract_from_jsonld`)
- **Validation:** Use `is_` or `_is_valid_` prefix (e.g., `is_date_in_range`, `is_valid_article_url`, `_is_valid_url`)
- **Boolean checks:** Prefix with `is_`, `has_`, `should_`, `can_`, `supports_` (e.g., `is_url_in_db`, `has_cf_cookies`, `supports_api_date_filter`)
- **Creation/initialization:** Use `create_`, `make_`, `init_` prefix (e.g., `create_article_item`, `_init_statistics`, `make_response`)
- **Cleanup/shutdown:** Use `close_`, `clean_`, `clear_` prefix (e.g., `closed()` for spider lifecycle)
- **Getting/retrieving:** Use `get_` prefix (e.g., `_get_db_connection`, `get_required_fields`)
- **Event handlers:** Use `handle_` or `on_` prefix (e.g., `handle_request_failure`, `from_crawler`)
- **Internal utilities:** Single underscore prefix for private (e.g., `_clean_author_name`, `_extract_author_from_jsonld`)

### Variables and Fields

- **Configuration/settings:** UPPER_CASE constants (e.g., `DEFAULT_START_DATE`, `DOWNLOAD_DELAY`)
- **Instance variables:** snake_case (e.g., `start_date`, `end_date`, `paper_name`, `processed_urls`)
- **Temporary/loop variables:** short snake_case (e.g., `date_obj`, `result`, `item`, `url`)
- **Scrapy Item fields:** snake_case (e.g., `article_body`, `publication_date`, `paper_name`, `image_url`)
- **Type hints:** Use on function signatures, e.g., `def parse_date(date_str: str, end_of_day: bool = False) -> datetime`

## Code Style

### Formatting

- **Tool:** Black (enforced via pre-commit)
- **Line length:** 88 characters (Black default, pyproject.toml specifies this)
- **Indentation:** 4 spaces (Python standard)

### Import Organization

**Order (enforced by isort with Black profile):**

1. Standard library imports (e.g., `import json`, `from datetime import datetime`)
2. Third-party imports (e.g., `import scrapy`, `import pytest`)
3. Local imports (e.g., `from BDNewsPaper.config import DHAKA_TZ`)

**Example from `base_spider.py`:**
```python
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Set

import pytz
import scrapy
from scrapy import signals
from scrapy.http import Request, Response

from BDNewsPaper.config import (
    DHAKA_TZ,
    DEFAULT_START_DATE,
    get_default_end_date,
    get_spider_config,
)
from BDNewsPaper.items import NewsArticleItem
```

**Multi-line imports:** Use parentheses with trailing comma (Black style)
```python
from BDNewsPaper.config import (
    DHAKA_TZ,
    DEFAULT_START_DATE,
    get_default_end_date,
)
```

### Path Aliases

No path aliases used. All imports use absolute package paths:
- `from BDNewsPaper.config import ...` (not relative imports)
- `from BDNewsPaper.spiders.base_spider import BaseNewsSpider`

## Error Handling

### Patterns

**Try-except blocks:** Catch specific exceptions, not bare `except:`
```python
try:
    dt = datetime.strptime(date_str, fmt)
except ValueError:
    continue
```

**Logging errors:** Use `self.logger` (Scrapy spider logger) for different levels
- `self.logger.error(...)` - Critical failures
- `self.logger.warning(...)` - Recoverable issues (timeouts, missing data)
- `self.logger.info(...)` - Significant events (spider startup, article found)
- `self.logger.debug(...)` - Detailed diagnostics (extraction details, skipped items)

**Example from `base_spider.py`:**
```python
except sqlite3.Error as e:
    self.logger.warning(f"Database check failed for {url}: {e}")
    return False

if not url.strip():
    return False

except (json.JSONDecodeError, TypeError, AttributeError) as e:
    self.logger.debug(f"JSON-LD parse error: {e}")
    continue
```

**Graceful degradation:** Chain fallback methods for extraction
```python
# Extract article data with fallbacks:
# 1. Try primary method (spider-specific selectors)
# 2. Fall back to JSON-LD extraction
# 3. Fall back to generic selectors
# 4. Fall back to meta tags
```

**Item validation:** Use Scrapy pipelines to validate items, not spiders
```python
# In spiders, create items with available data
item = NewsArticleItem(url=url, headline=headline, ...)

# In pipelines, validate and reject
if not adapter.get('headline'):
    raise DropItem(f"Missing headline: {url}")
```

## Logging

### Framework

**Tool:** Python's standard `logging` module via Scrapy's `self.logger`
- Accessed in spiders as `self.logger`
- Configured in `BDNewsPaper/settings.py`

### Patterns

**Spider initialization:**
```python
self.logger.info(f"Spider {self.name} initialized")
self.logger.info(f"Date range: {self.start_date} to {self.end_date}")
if self.categories:
    self.logger.info(f"Categories: {self.categories}")
```

**Extraction progress:**
```python
self.logger.debug(f"Extracted from JSON-LD: {result.get('headline')[:50]}")
self.logger.info(f"Discovered {len(article_urls)} article links")
```

**Errors and warnings:**
```python
self.logger.warning(f"DNS lookup failed for {url}")
self.logger.error(f"Request failed for {url}: {error_msg}")
```

**Statistics on completion:**
```python
self.logger.info("=" * 60)
self.logger.info(f"Articles processed: {self.stats['articles_processed']}")
self.logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
```

## Comments

### When to Comment

- **Complex logic:** Explain why, not what
  ```python
  # Swap if dates are in wrong order (user provided start > end)
  if self.start_date > self.end_date:
      self.start_date, self.end_date = self.end_date, self.start_date
  ```

- **Non-obvious decisions:**
  ```python
  # Filter invalid patterns before creating requests to prevent
  # ValidationPipeline drops (optimization)
  if not self.is_valid_article_url(url):
      continue
  ```

- **Extraction strategy explanation:**
  ```python
  # Try JSON-LD first (most reliable)
  result = self.extract_from_jsonld(response)
  ```

### Documentation Style

**Module docstrings:** Triple-quoted description with sections
```python
"""
Base Spider Class for BDNewsPaper Scrapers
===========================================
Common functionality shared by all newspaper spiders.
"""
```

**Class docstrings:** Include features and usage
```python
class BaseNewsSpider(scrapy.Spider):
    """
    Base class for all newspaper spiders with common functionality.

    Features:
        - Standardized date range parsing
        - Category filtering support
        - Database duplicate checking
        - Statistics tracking
        - Common error handling

    Child classes should override:
        - paper_name: Name of the newspaper
        - start_requests(): Generate initial requests
        - parse(): Parse responses
    """
```

**Function docstrings:** Include Args, Returns, and notes
```python
def extract_from_jsonld(self, response: Response) -> Optional[Dict[str, Any]]:
    """
    Extract article data from JSON-LD structured data.

    Most news sites embed article metadata in JSON-LD format.
    This is the most reliable extraction method when available.

    Args:
        response: Scrapy Response object

    Returns:
        Dictionary with extracted fields, or None if not found
    """
```

**Method grouping:** Use comment headers to organize related methods
```python
# ================================================================
# Database Operations (Thread-Safe)
# ================================================================

def _get_db_connection(self):
    """Get thread-local database connection."""

def is_url_in_db(self, url: str) -> bool:
    """Check if URL already exists in database."""
```

## Function Design

### Size Guidelines

- **Small functions:** Under 20 lines (extraction, validation, transformation)
- **Medium functions:** 20-50 lines (parsing, request generation)
- **Large functions:** Use only when necessary; break into helper methods

**Example (large but well-organized):**
```python
def extract_author(self, response: Response) -> Optional[str]:
    """Extract author using 4 strategies in order."""
    # Strategy 1: JSON-LD
    author = self._try_jsonld_author(response)
    if author:
        return author

    # Strategy 2: Meta tags
    author = self._try_meta_tags(response)
    if author:
        return author

    # Strategy 3: Byline patterns
    author = self._try_byline_patterns(response)
    if author:
        return author

    return None
```

### Parameters

**Prefer keyword arguments for clarity:**
```python
def create_article_item(self, **kwargs) -> NewsArticleItem:
    """Create standardized article item with common fields."""
    item = NewsArticleItem()
    item['paper_name'] = kwargs.get('paper_name', self.paper_name)
```

**Type hints required on public methods:**
```python
def is_date_in_range(self, date_obj: datetime) -> bool:
    """Check if date is within configured range."""
```

**Default arguments for optional parameters:**
```python
def discover_links(self, response: Response, limit: int = 50) -> List[str]:
    """Discover article links up to limit."""
```

### Return Values

**Be explicit about None returns:**
```python
def extract_from_jsonld(self, response: Response) -> Optional[Dict[str, Any]]:
    """Returns dict or None."""
    if not data:
        return None
    return result
```

**Return early to reduce nesting:**
```python
def is_valid_article_url(self, url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return False
    if not url.strip():
        return False
    # ... continue checks
    return True
```

## Module Design

### Exports

**Scrapy Item fields:** All fields defined with processors in `items.py`
```python
headline = scrapy.Field(
    input_processor=Compose(clean_text),
    output_processor=TakeFirst(),
)
```

**Pipeline classes:** All inherit from base, implement `from_crawler` class method
```python
class ValidationPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls(...)

    def process_item(self, item, spider):
        return item
```

**Spider classes:** All inherit from `BaseNewsSpider`, define `name` and `paper_name`
```python
class ProthomaloSpider(BaseNewsSpider):
    name = "prothomalo"
    paper_name = "Prothom Alo"
```

### Configuration

**Settings in `BDNewsPaper/config.py`:**
- Timezone constants: `DHAKA_TZ`
- Database paths: `DEFAULT_DB_PATH`
- Date ranges: `DEFAULT_START_DATE`
- Spider configurations: `SPIDER_CONFIGS` dict
- Validation thresholds: `MIN_ARTICLE_LENGTH`, `MIN_HEADLINE_LENGTH`

**Scrapy settings in `BDNewsPaper/settings.py`:**
- Middleware priorities
- Pipeline priorities
- Download delays and throttling
- Custom settings (spiders override in `custom_settings` class attribute)

## Type Hints

**Always include on public methods:**
```python
def parse_date(self, date_str: str, end_of_day: bool = False) -> datetime:
def is_date_in_range(self, date_obj: datetime) -> bool:
def create_article_item(self, **kwargs) -> NewsArticleItem:
```

**Use Optional for nullable values:**
```python
def extract_author(self, response: Response) -> Optional[str]:
def get_spider_config(spider_name: str) -> Optional[SpiderConfig]:
```

**Use typing collections for complex types:**
```python
from typing import Dict, List, Generator, Set, Tuple

def discover_links(self) -> List[str]:
def _init_statistics(self) -> None:
def start_requests(self) -> Generator[scrapy.Request, None, None]:
```

---

*Convention analysis: 2026-03-17*
