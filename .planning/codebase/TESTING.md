# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

### Runner

- **Framework:** pytest 9.0.0+
- **Config:** `pyproject.toml` under `[tool.pytest.ini_options]`
- **Test location:** `tests/` directory

**Configuration in pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--tb=short",
    "--cov=BDNewsPaper",
    "--cov-report=term-missing",
    "--cov-report=html",
]
```

### Assertion Library

- **Library:** pytest's built-in assertions (no external assertion library)
- **Usage:** Standard Python `assert` statements with pytest introspection

### Run Commands

```bash
pytest tests/                          # Run all tests
pytest tests/ -v                       # Verbose output
pytest tests/ --cov=BDNewsPaper        # With coverage report
pytest tests/ -k test_validation       # Run specific test
pytest tests/ --cov --cov-report=html  # HTML coverage report
pytest tests/ -x                       # Stop on first failure
pytest tests/ --tb=short               # Short traceback
```

**Pre-commit hook:** Tests run at push stage
```yaml
- id: pytest-check
  name: pytest-check
  entry: pytest tests/ -x --tb=short
  language: system
  pass_filenames: false
  always_run: true
  stages: [push]
```

## Test File Organization

### Location

- **Pattern:** Co-located with source code in `tests/` directory
- **Directory structure:**
  ```
  tests/
  ├── __init__.py
  ├── conftest.py              # Shared fixtures
  ├── test_smoke.py            # Integration/smoke tests
  ├── test_pipelines.py        # Pipeline unit tests
  ├── test_middlewares.py      # Middleware unit tests
  ├── test_extractors.py       # Extractor unit tests
  ├── test_cloudflare_bypass.py # Anti-bot tests
  ├── test_integration.py      # Integration tests
  └── fixtures/                # HTML/JSON test data (if needed)
  ```

### Naming

- **Test files:** Prefix with `test_` (e.g., `test_pipelines.py`, `test_smoke.py`)
- **Test classes:** Prefix with `Test` (e.g., `TestValidationPipeline`, `TestExtractionResult`)
- **Test methods:** Prefix with `test_` (e.g., `test_validation_pipeline`, `test_extract_headline`)

### Structure

**Example test file layout:**
```python
"""
Module docstring explaining test focus.
"""

import pytest
from unittest.mock import MagicMock, patch

# Test data/constants at top
SAMPLE_HTML_JSONLD = """..."""

# Organized by test class
class TestClassName:
    """Group related tests in classes."""

    @pytest.fixture
    def fixture_name(self):
        """Fixtures for this test class."""
        return value

    def test_method_name(self, fixture_name):
        """Test specific behavior."""
        # Arrange
        result = function_under_test()

        # Assert
        assert result == expected
```

## Test Structure

### Suite Organization

**Pytest marks by test type:**
```python
class TestValidationPipeline:
    """Tests for ValidationPipeline class."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance."""
        return ValidationPipeline()

    @pytest.fixture
    def valid_item(self):
        """Create valid article item."""
        return NewsArticleItem(
            headline="Test Headline",
            article_body="Content " * 20,
            url="https://example.com/article",
            paper_name="Test Paper",
        )

    def test_accepts_valid_item(self, pipeline, valid_item, mock_spider):
        """Test pipeline accepts valid items."""
        result = pipeline.process_item(valid_item, mock_spider)
        assert result['headline'] == valid_item['headline']

    def test_rejects_invalid_item(self, pipeline, mock_spider):
        """Test pipeline rejects invalid items."""
        invalid = NewsArticleItem(
            headline="",
            article_body="Short",
            url="invalid-url",
            paper_name="",
        )
        with pytest.raises(DropItem):
            pipeline.process_item(invalid, mock_spider)
```

### Setup and Teardown

**Using pytest fixtures (preferred):**
```python
@pytest.fixture
def mock_spider():
    """Create a mock spider for testing."""
    spider = MagicMock(spec=scrapy.Spider)
    spider.name = 'test_spider'
    spider.logger = MagicMock()
    return spider


@pytest.fixture
def mock_crawler():
    """Create a mock crawler with settings."""
    crawler = MagicMock()
    crawler.settings = MagicMock()
    crawler.settings.get = lambda key, default=None: default
    crawler.settings.getint = lambda key, default=None: default
    return crawler
```

**Fixture scope:**
- `function` (default) - New instance per test
- `class` - Shared per test class
- `module` - Shared per module
- `session` - Shared across entire test run

**Example from `conftest.py`:**
```python
@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / 'test_articles.db')


@pytest.fixture
def make_response():
    """Factory fixture to create mock HTML responses."""
    def _make_response(html_content: str, url: str = 'http://test.com/article'):
        request = Request(url=url)
        response = HtmlResponse(
            url=url,
            request=request,
            body=html_content.encode('utf-8'),
            encoding='utf-8',
        )
        return response
    return _make_response
```

### Assertion Patterns

**Item validation:**
```python
assert result['headline'] == expected_headline
assert 'article_body' in result
assert result['url'].startswith('https://')
```

**Exception testing:**
```python
with pytest.raises(DropItem) as exc_info:
    pipeline.process_item(invalid_item, spider)
assert "Missing required field" in str(exc_info.value)
```

**Response checking:**
```python
assert response.status == 200
assert '<html>' in response.text
assert response.xpath('//article').get() is not None
```

**List/dict assertions:**
```python
assert len(requests) > 0
assert all(isinstance(r, Request) for r in requests)
assert 'User-Agent' in request.headers
```

## Mocking

### Framework

- **Tool:** `unittest.mock` (Python standard library)
- **Access pattern:** `from unittest.mock import MagicMock, patch`

### Patterns

**Mock Spider:**
```python
spider = MagicMock(spec=scrapy.Spider)
spider.name = 'test_spider'
spider.logger = MagicMock()
spider.stats = {'processed': 0}
```

**Mock Response:**
```python
request = Request(url='https://example.com/article')
response = HtmlResponse(
    url='https://example.com/article',
    request=request,
    body=b'<html>content</html>',
    encoding='utf-8',
)
```

**Mock Crawler:**
```python
crawler = MagicMock()
crawler.settings = Settings({
    'DATABASE_PATH': ':memory:',
    'MIN_ARTICLE_LENGTH': 50,
})
crawler.signals = MagicMock()
```

**Patch decorator:**
```python
@patch('BDNewsPaper.extractors.FallbackExtractor')
def test_extraction_fallback(self, mock_extractor):
    """Test fallback extraction pipeline."""
    mock_extractor.return_value.extract.return_value = {
        'headline': 'Test',
        'body': 'Content' * 20,
    }
    # Test code
```

### What to Mock

- **External services:** HTTP requests, databases, APIs
- **Expensive operations:** File I/O, complex calculations
- **Spider logger:** Avoid cluttering test output
- **Settings/Crawler:** Scrapy infrastructure objects

**Example from `test_smoke.py`:**
```python
def test_middleware_chain_no_conflicts(self, mock_crawler, mock_spider):
    """Test that middleware chain processes requests without conflicts."""
    stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
    cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)

    request = Request(url='https://example.com/article')
    result1 = stealth.process_request(request, mock_spider)
    result2 = cf_bypass.process_request(request, mock_spider)

    assert result1 is None  # Should pass through
    assert result2 is None  # Should pass through
```

### What NOT to Mock

- **Item classes:** Test with real `NewsArticleItem` instances
- **Field processors:** Test actual cleaning/validation logic
- **Pipeline logic:** Should process real data
- **Helper functions:** Test as-is to catch real bugs

**Example - test with real items:**
```python
def test_validation_pipeline(self, mock_spider):
    """Test ValidationPipeline with real items."""
    pipeline = ValidationPipeline()

    # Use real NewsArticleItem, not mock
    item = NewsArticleItem(
        headline="Real Headline",
        article_body="Real content " * 20,
        url="https://example.com",
        paper_name="Test Paper",
    )

    result = pipeline.process_item(item, mock_spider)
    assert result['headline'] == item['headline']
```

## Fixtures and Factories

### Test Data

**Sample HTML in `conftest.py`:**
```python
@pytest.fixture
def sample_article_html():
    """Sample article HTML for testing parsers."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": "Test Headline from JSON-LD",
            "articleBody": "This is the article body from JSON-LD...",
            "datePublished": "2024-12-25T10:00:00+06:00"
        }
        </script>
    </head>
    <body>
        <article>
            <h1>Test Headline</h1>
            <div class="article-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
            </div>
        </article>
    </body>
    </html>
    """
```

**Item factories:**
```python
@pytest.fixture
def valid_article_item():
    """Create a valid NewsArticleItem for testing."""
    return NewsArticleItem(
        headline="Test Headline with Sufficient Length",
        article_body="This is a test article body with enough content. " * 10,
        url="https://example.com/test-article",
        paper_name="Test Paper",
        publication_date="2024-12-25T10:00:00+06:00",
        category="Test",
        author="Test Author",
    )


@pytest.fixture
def minimal_article_item():
    """Create minimal item with only required fields."""
    return NewsArticleItem(
        headline="Minimal Headline",
        article_body="Short body" * 10,
        url="https://example.com/minimal",
        paper_name="Test Paper",
    )


@pytest.fixture
def invalid_article_item():
    """Create invalid item for negative testing."""
    return NewsArticleItem(
        headline="",  # Empty
        article_body="Short",  # Too short
        url="invalid-url",  # Invalid URL
        paper_name="",
    )
```

### Location

- **Shared fixtures:** `tests/conftest.py`
- **Test-specific fixtures:** In individual test files
- **Test data files:** `tests/fixtures/` directory (if needed)

## Coverage

### Requirements

- **Target:** No explicit target enforced in settings (optional)
- **Tool:** pytest-cov 7.0.0+
- **Report types:** terminal (missing lines), HTML

### View Coverage

```bash
# Terminal report
pytest tests/ --cov=BDNewsPaper --cov-report=term-missing

# HTML report (opens htmlcov/index.html)
pytest tests/ --cov=BDNewsPaper --cov-report=html
open htmlcov/index.html
```

**Exclude from coverage (in pyproject.toml):**
```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Test Types

### Unit Tests

**Scope:** Single function or method

**Example - Item field processor:**
```python
def test_clean_text_removes_html():
    """Test clean_text processor removes HTML tags."""
    from BDNewsPaper.items import clean_text

    result = clean_text("<p>Test content</p>")
    assert "<p>" not in result
    assert "Test content" in result
```

**Example - Validation:**
```python
def test_is_valid_article_url_rejects_javascript():
    """Test URL validation rejects javascript: links."""
    from BDNewsPaper.spiders.base_spider import BaseNewsSpider

    spider = BaseNewsSpider()
    assert spider.is_valid_article_url("javascript:void(0)") is False
    assert spider.is_valid_article_url("https://example.com") is True
```

### Integration Tests

**Scope:** Multiple components working together

**Example - Pipeline chain:**
```python
def test_pipeline_chain_no_conflicts(self, mock_spider):
    """Test full pipeline chain processes item."""
    validation = ValidationPipeline()
    clean = CleanArticlePipeline()
    language = LanguageDetectionPipeline()

    item = valid_article_item
    item = validation.process_item(item, mock_spider)
    item = clean.process_item(item, mock_spider)
    item = language.process_item(item, mock_spider)

    assert item['headline']
    assert item['article_body']
```

**Example - Middleware chain:**
```python
def test_all_middleware_together(self, mock_crawler, mock_spider):
    """Test ALL middleware process requests without conflicts."""
    stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
    cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)
    retry = SmartRetryMiddleware(mock_crawler.settings)

    request = Request(url='https://example.com/article')

    for mw in [stealth, cf_bypass, retry]:
        result = mw.process_request(request, mock_spider)
        assert result is None or isinstance(result, Request)

    assert 'User-Agent' in request.headers
```

### Smoke Tests

**Scope:** Entire system can initialize and process without errors

**Example - Module imports:**
```python
def test_all_bdnewspaper_modules_import(self, bdnewspaper_modules):
    """Test that all BDNewsPaper modules can be imported."""
    failed_imports = []

    for module_name in bdnewspaper_modules:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            failed_imports.append((module_name, str(e)))

    if failed_imports:
        pytest.fail(f"Failed to import {len(failed_imports)} modules")
```

**Example - Settings validation:**
```python
def test_middleware_order_valid(self):
    """Test that middleware priorities don't conflict."""
    from BDNewsPaper import settings

    middlewares = settings.DOWNLOADER_MIDDLEWARES
    priorities = [v for v in middlewares.values() if v is not None]

    # Check no duplicate priorities
    assert len(priorities) == len(set(priorities))
```

## Common Patterns

### Async Testing

Not used in this codebase. Scrapy handles async internally; tests are synchronous.

### Error Testing

**Test exception raising:**
```python
def test_validation_pipeline_rejects_invalid(self, mock_spider):
    """Test ValidationPipeline rejects invalid items."""
    from scrapy.exceptions import DropItem
    from BDNewsPaper.pipelines import ValidationPipeline

    pipeline = ValidationPipeline()
    invalid_item = NewsArticleItem(
        headline="",
        article_body="Short",
        url="invalid",
        paper_name="",
    )

    with pytest.raises(DropItem):
        pipeline.process_item(invalid_item, mock_spider)
```

**Test error handling in extraction:**
```python
def test_extract_from_jsonld_handles_invalid_json():
    """Test JSON-LD extractor handles malformed JSON."""
    # Response with broken JSON-LD
    response = make_response("""
    <script type="application/ld+json">
    { invalid json
    </script>
    """)

    result = extractor.extract_from_jsonld(response)
    # Should return None, not raise exception
    assert result is None
```

### Parametrized Tests

**Test multiple inputs with one test function:**
```python
@pytest.mark.parametrize("input_date,expected_valid", [
    ("2024-12-25", True),
    ("invalid", False),
    ("2024-13-45", False),
])
def test_parse_date_handles_formats(input_date, expected_valid):
    """Test date parser with multiple formats."""
    try:
        result = parse_date(input_date)
        assert expected_valid is True
    except ValueError:
        assert expected_valid is False
```

### Database Testing

**Use in-memory SQLite:**
```python
@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database for testing."""
    return str(tmp_path / 'test.db')

def test_spider_database_operations(self, temp_db_path):
    """Test spider database interactions."""
    spider = TestSpider(db_path=temp_db_path)

    # Initialize database
    spider.setup_db()

    # Test operations
    spider.add_url("https://example.com/article")
    assert spider.is_url_in_db("https://example.com/article")
```

---

*Testing analysis: 2026-03-17*
