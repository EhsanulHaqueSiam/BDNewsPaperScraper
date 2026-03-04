# Test Suite Documentation

This document explains what each test file does and how to run tests.

## Quick Start

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=BDNewsPaper --cov-report=html

# Run specific test file
uv run pytest tests/test_smoke.py -v

# Run specific test class
uv run pytest tests/test_smoke.py::TestMiddlewareIntegration -v
```

---

## Test Files Overview

### `test_smoke.py` (539 lines)
**Purpose:** Comprehensive integration tests to ensure all components work together.

| Test Class | What It Tests |
|------------|---------------|
| `TestSyntaxValidation` | All Python files import without errors |
| `TestMiddlewareIntegration` | Middleware chain processes requests correctly |
| `TestPipelineIntegration` | Pipeline chain processes items correctly |
| `TestSpiderSmoke` | Spiders have required attributes and methods |
| `TestFullIntegration` | Settings, priorities, and schemas are valid |
| `TestAllSpidersImport` | All 80+ spider modules import without errors |

**Key Tests:**
- `test_middleware_chain_no_conflicts` - Verifies middlewares don't conflict
- `test_pipeline_chain_no_conflicts` - Verifies pipelines work in sequence
- `test_all_spiders_import` - Imports every spider module

---

### `test_extractors.py` (230 lines)
**Purpose:** Tests the Smart Fallback Extraction system.

| Test Class | What It Tests |
|------------|---------------|
| `TestExtractionResult` | Extraction result validation and serialization |
| `TestJSONLDExtractor` | JSON-LD structured data extraction |
| `TestHeuristicExtractor` | CSS selector-based extraction |
| `TestFallbackExtractor` | Full fallback chain (JSON-LD → Trafilatura → Heuristics) |
| `TestEdgeCases` | Empty HTML, malformed JSON-LD, Bengali content |

**Key Tests:**
- `test_extract_from_jsonld` - Tests structured data extraction
- `test_fallback_chain_jsonld_first` - Verifies fallback order
- `test_bengali_content` - Tests Bengali (বাংলা) text extraction

---

### `test_cloudflare_bypass.py` (11KB)
**Purpose:** Tests Cloudflare protection detection and bypass.

| Test Class | What It Tests |
|------------|---------------|
| `TestCloudflareDetector` | Challenge page detection (403, 429, JS challenges) |
| `TestCloudflareCookieCache` | Cookie caching and persistence |
| `TestCloudflareBypassMiddleware` | Middleware initialization and processing |
| `TestHelperFunctions` | Stealth JS and Playwright options |

**Key Tests:**
- `test_detects_challenge_page` - Detects "Just a moment..." page
- `test_detects_cf_turnstile` - Detects Turnstile CAPTCHA
- `test_process_response_detects_challenge` - Response processing

---

### `test_middlewares.py` (8KB)
**Purpose:** Tests individual middleware components.

| Test Class | What It Tests |
|------------|---------------|
| `TestSmartRetryMiddleware` | Exponential backoff retry logic |
| `TestCircuitBreakerMiddleware` | Circuit breaker state transitions |
| `TestAdaptiveThrottlingMiddleware` | Dynamic delay adjustment |
| `TestUserAgentMiddleware` | User-Agent rotation |

**Key Tests:**
- `test_circuit_breaker_opens_after_failures` - CLOSED → OPEN transition
- `test_adaptive_throttle_increases_on_slow` - Delay adjustment

---

### `test_pipelines.py` (9KB)
**Purpose:** Tests item processing pipelines.

| Test Class | What It Tests |
|------------|---------------|
| `TestValidationPipeline` | Item validation (required fields, URL format) |
| `TestCleanArticlePipeline` | HTML cleaning, whitespace normalization |
| `TestLanguageDetectionPipeline` | Language detection and filtering |
| `TestContentQualityPipeline` | Word count, reading time calculation |
| `TestFallbackExtractionPipeline` | Content rescue for failed extractions |

**Key Tests:**
- `test_validation_drops_missing_headline` - Rejects invalid items
- `test_clean_removes_html` - HTML tag removal
- `test_language_detection` - Detects English/Bengali

---

## Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Middlewares | ~40% | 60%+ |
| Pipelines | ~50% | 70%+ |
| Spiders | ~20% | 30%+ |
| Extractors | ~60% | 80%+ |
| **Overall** | **23%** | **40%+** |

---

## Running Specific Tests

```bash
# Test only middleware
uv run pytest tests/test_middlewares.py -v

# Test only pipelines
uv run pytest tests/test_pipelines.py -v

# Test extraction system
uv run pytest tests/test_extractors.py -v

# Test Cloudflare bypass
uv run pytest tests/test_cloudflare_bypass.py -v

# Run smoke tests (comprehensive)
uv run pytest tests/test_smoke.py -v

# Run with verbose output and stop on first failure
uv run pytest -v -x

# Run with parallel execution (requires pytest-xdist)
uv run pytest -n auto
```
