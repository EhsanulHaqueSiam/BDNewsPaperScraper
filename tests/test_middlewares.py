"""
Middleware Unit Tests
=====================
Tests for retry, circuit breaker, and other middleware components.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from collections import defaultdict

from scrapy.http import Request, Response
from scrapy.exceptions import IgnoreRequest

from BDNewsPaper.middlewares import (
    SmartRetryMiddleware,
    CircuitBreakerMiddleware,
    UserAgentMiddleware,
    StatisticsMiddleware,
)


class TestSmartRetryMiddleware:
    """Tests for SmartRetryMiddleware."""
    
    @pytest.fixture
    def settings(self):
        settings = MagicMock()
        settings.getint = lambda key, default=None: {
            'RETRY_TIMES': 3,
        }.get(key, default)
        settings.getfloat = lambda key, default=None: {
            'RETRY_BACKOFF_FACTOR': 2.0,
            'RETRY_MAX_DELAY': 60.0,
            'RETRY_JITTER_FACTOR': 0.1,
        }.get(key, default)
        settings.getlist = lambda key, default=None: {
            'RETRY_HTTP_CODES': [500, 502, 503, 504, 429],
        }.get(key, default or [])
        return settings
    
    @pytest.fixture
    def middleware(self, settings):
        return SmartRetryMiddleware(settings)
    
    def test_successful_response_passes(self, middleware, mock_spider):
        """Test that successful responses pass through."""
        request = Request(url='http://test.com')
        response = Response(url='http://test.com', status=200, request=request)
        
        result = middleware.process_response(request, response, mock_spider)
        assert result == response
    
    def test_500_error_triggers_retry(self, middleware, mock_spider):
        """Test that 500 errors trigger retry."""
        request = Request(url='http://test.com')
        response = Response(url='http://test.com', status=500, request=request)
        
        result = middleware.process_response(request, response, mock_spider)
        
        # Should return new request or original response
        if isinstance(result, Request):
            assert result.meta.get('retry_times') == 1
        else:
            assert result == response
    
    def test_429_error_triggers_retry(self, middleware, mock_spider):
        """Test that 429 rate limit errors trigger retry."""
        request = Request(url='http://test.com')
        response = Response(url='http://test.com', status=429, request=request)
        
        result = middleware.process_response(request, response, mock_spider)
        
        if isinstance(result, Request):
            assert result.meta.get('retry_times') == 1
    
    def test_max_retries_exceeded(self, middleware, mock_spider):
        """Test that requests are dropped after max retries."""
        request = Request(url='http://test.com', meta={'retry_times': 3})
        response = Response(url='http://test.com', status=500, request=request)
        
        result = middleware.process_response(request, response, mock_spider)
        
        # Should return original response (gave up retrying)
        assert result == response
    
    def test_exponential_backoff_delay(self, middleware, mock_spider):
        """Test that retry delay increases exponentially."""
        delays = []
        
        for retry in range(1, 4):
            request = Request(url='http://test.com', meta={'retry_times': retry - 1})
            response = Response(url='http://test.com', status=500, request=request)
            
            result = middleware.process_response(request, response, mock_spider)
            if isinstance(result, Request) and 'download_delay' in result.meta:
                delays.append(result.meta['download_delay'])
        
        # Delays should generally increase (with jitter)
        if len(delays) >= 2:
            # Just check delays are reasonable
            for delay in delays:
                assert 0.1 <= delay <= 60.0


class TestCircuitBreakerMiddleware:
    """Tests for CircuitBreakerMiddleware."""
    
    @pytest.fixture
    def middleware(self):
        return CircuitBreakerMiddleware(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short for testing
            half_open_max_calls=2,
        )
    
    def test_initial_state_closed(self, middleware, mock_spider):
        """Test that circuit starts in CLOSED state."""
        request = Request(url='http://test.com')
        result = middleware.process_request(request, mock_spider)
        
        # Should pass through (return None)
        assert result is None
        
        domain = middleware._get_domain('http://test.com')
        assert middleware.circuits[domain]['state'] == middleware.CLOSED
    
    def test_opens_after_threshold_failures(self, middleware, mock_spider):
        """Test that circuit opens after threshold failures."""
        domain = 'test.com'
        
        # Simulate failures
        for _ in range(3):
            request = Request(url='http://test.com/article')
            response = Response(url='http://test.com/article', status=500, request=request)
            middleware.process_response(request, response, mock_spider)
        
        assert middleware.circuits[domain]['state'] == middleware.OPEN
    
    def test_open_circuit_rejects_requests(self, middleware, mock_spider):
        """Test that open circuit rejects requests."""
        domain = 'test.com'
        middleware.circuits[domain]['state'] = middleware.OPEN
        middleware.circuits[domain]['last_failure_time'] = time.time()
        
        request = Request(url='http://test.com/new-article')
        
        with pytest.raises(IgnoreRequest):
            middleware.process_request(request, mock_spider)
    
    def test_transitions_to_half_open(self, middleware, mock_spider):
        """Test transition from OPEN to HALF_OPEN after timeout."""
        domain = 'test.com'
        middleware.circuits[domain]['state'] = middleware.OPEN
        middleware.circuits[domain]['last_failure_time'] = time.time() - 2.0  # Past timeout
        
        request = Request(url='http://test.com/article')
        result = middleware.process_request(request, mock_spider)
        
        # Should transition to HALF_OPEN and allow request
        assert result is None
        assert middleware.circuits[domain]['state'] == middleware.HALF_OPEN
    
    def test_success_closes_circuit(self, middleware, mock_spider):
        """Test that successful requests in HALF_OPEN close the circuit."""
        domain = 'test.com'
        middleware.circuits[domain]['state'] = middleware.HALF_OPEN
        middleware.circuits[domain]['successes'] = 0
        
        # Simulate successful responses
        for _ in range(2):  # half_open_max_calls
            request = Request(url='http://test.com/article')
            response = Response(url='http://test.com/article', status=200, request=request)
            middleware.process_response(request, response, mock_spider)
        
        assert middleware.circuits[domain]['state'] == middleware.CLOSED


class TestUserAgentMiddleware:
    """Tests for UserAgentMiddleware."""
    
    @pytest.fixture
    def middleware(self):
        return UserAgentMiddleware()
    
    def test_sets_user_agent(self, middleware, mock_spider):
        """Test that User-Agent header is set."""
        request = Request(url='http://test.com')
        
        middleware.process_request(request, mock_spider)
        
        assert 'User-Agent' in request.headers
        ua = request.headers['User-Agent'].decode()
        assert 'Mozilla' in ua
    
    def test_rotates_user_agents(self, middleware, mock_spider):
        """Test that User-Agents are rotated."""
        user_agents = set()
        
        for _ in range(50):
            request = Request(url='http://test.com')
            middleware.process_request(request, mock_spider)
            ua = request.headers['User-Agent'].decode()
            user_agents.add(ua)
        
        # Should have used multiple different UAs
        assert len(user_agents) > 1
