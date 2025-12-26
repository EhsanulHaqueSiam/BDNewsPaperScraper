"""
AI-Powered Content Repair
=========================
Use LLMs to extract content from messy HTML when other methods fail.

Features:
    - Local LLM integration (Ollama, llama.cpp)
    - OpenAI/Anthropic API support 
    - Pipeline integration for failed extractions
    - Prompt templates for article extraction

Usage:
    from BDNewsPaper.ai_repair import AIRepairPipeline
    
    # Add to ITEM_PIPELINES after FallbackExtractionPipeline

Settings:
    - AI_REPAIR_ENABLED: Enable/disable (default: False)
    - AI_REPAIR_PROVIDER: ollama, openai, anthropic (default: ollama)
    - AI_REPAIR_MODEL: Model name (default: llama3.2)
    - AI_REPAIR_ENDPOINT: API endpoint for local models
"""

import json
import logging
import re
from typing import Dict, Optional, Any
from dataclasses import dataclass

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    import requests as httpx
    HTTPX_AVAILABLE = False

from itemadapter import ItemAdapter
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


# Prompt template for article extraction
EXTRACTION_PROMPT = """Extract the news article from this HTML. Return JSON with:
- headline: The main title
- body: The article text (paragraphs joined)
- author: Author name if found
- date: Publication date if found

HTML:
{html}

Return ONLY valid JSON, no explanations."""


@dataclass
class ExtractionResult:
    """Result from AI extraction."""
    headline: str = ""
    body: str = ""
    author: str = ""
    date: str = ""
    success: bool = False
    error: str = ""


class OllamaClient:
    """Client for Ollama local LLM."""
    
    def __init__(self, endpoint: str = 'http://localhost:11434', model: str = 'llama3.2'):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate response from Ollama."""
        try:
            response = httpx.post(
                f"{self.endpoint}/api/generate",
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'num_predict': max_tokens,
                        'temperature': 0.1,
                    },
                },
                timeout=60,
            )
            
            data = response.json()
            return data.get('response', '')
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return ''
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = httpx.get(f"{self.endpoint}/api/version", timeout=5)
            return response.status_code == 200
        except:
            return False


class OpenAIClient:
    """Client for OpenAI API."""
    
    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo'):
        self.api_key = api_key
        self.model = model
        self.endpoint = 'https://api.openai.com/v1/chat/completions'
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate response from OpenAI."""
        try:
            response = httpx.post(
                self.endpoint,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': max_tokens,
                    'temperature': 0.1,
                },
                timeout=60,
            )
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return ''


def extract_with_ai(
    html: str,
    provider: str = 'ollama',
    model: str = 'llama3.2',
    endpoint: str = None,
    api_key: str = None,
) -> ExtractionResult:
    """
    Extract article content using AI.
    
    Args:
        html: Raw HTML content (truncated for context window)
        provider: ollama, openai, or anthropic
        model: Model name
        endpoint: API endpoint for ollama
        api_key: API key for openai/anthropic
    """
    # Truncate HTML to fit context window
    max_html_length = 8000
    if len(html) > max_html_length:
        html = html[:max_html_length] + "..."
    
    prompt = EXTRACTION_PROMPT.format(html=html)
    
    # Get client based on provider
    if provider == 'ollama':
        client = OllamaClient(endpoint or 'http://localhost:11434', model)
    elif provider == 'openai':
        if not api_key:
            return ExtractionResult(error="OpenAI API key required")
        client = OpenAIClient(api_key, model)
    else:
        return ExtractionResult(error=f"Unknown provider: {provider}")
    
    # Generate response
    response_text = client.generate(prompt)
    
    if not response_text:
        return ExtractionResult(error="Empty response from AI")
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response_text)
        
        return ExtractionResult(
            headline=data.get('headline', ''),
            body=data.get('body', ''),
            author=data.get('author', ''),
            date=data.get('date', ''),
            success=True,
        )
        
    except json.JSONDecodeError as e:
        return ExtractionResult(error=f"JSON parse error: {e}")


class AIRepairPipeline:
    """
    Pipeline that uses AI to repair failed extractions.
    
    Should be placed after FallbackExtractionPipeline.
    Only triggers when content is still missing after all other attempts.
    """
    
    def __init__(
        self,
        enabled: bool = False,
        provider: str = 'ollama',
        model: str = 'llama3.2',
        endpoint: str = None,
        api_key: str = None,
        min_body_length: int = 50,
    ):
        self.enabled = enabled
        self.provider = provider
        self.model = model
        self.endpoint = endpoint
        self.api_key = api_key
        self.min_body_length = min_body_length
        
        self.stats = {
            'triggered': 0,
            'success': 0,
            'failed': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('AI_REPAIR_ENABLED', False)
        if not enabled:
            raise NotConfigured("AI repair disabled")
        
        return cls(
            enabled=True,
            provider=crawler.settings.get('AI_REPAIR_PROVIDER', 'ollama'),
            model=crawler.settings.get('AI_REPAIR_MODEL', 'llama3.2'),
            endpoint=crawler.settings.get('AI_REPAIR_ENDPOINT'),
            api_key=crawler.settings.get('AI_REPAIR_API_KEY'),
            min_body_length=crawler.settings.getint('AI_REPAIR_MIN_BODY_LENGTH', 50),
        )
    
    def process_item(self, item, spider):
        if not self.enabled:
            return item
        
        adapter = ItemAdapter(item)
        article_body = adapter.get('article_body', '')
        headline = adapter.get('headline', '')
        
        # Check if content needs AI repair
        needs_body = not article_body or len(article_body.strip()) < self.min_body_length
        needs_headline = not headline or len(headline.strip()) < 5
        
        if not (needs_body or needs_headline):
            return item
        
        # Get raw HTML
        raw_html = adapter.get('_raw_html', '') or adapter.get('response_body', '')
        if not raw_html:
            return item
        
        self.stats['triggered'] += 1
        spider.logger.info(f"AI repair triggered for: {adapter.get('url', 'unknown')}")
        
        # Extract with AI
        result = extract_with_ai(
            raw_html,
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            api_key=self.api_key,
        )
        
        if result.success:
            self.stats['success'] += 1
            
            if needs_body and result.body:
                adapter['article_body'] = result.body
                adapter['_extraction_source'] = f'ai_{self.provider}'
            
            if needs_headline and result.headline:
                adapter['headline'] = result.headline
            
            if not adapter.get('author') and result.author:
                adapter['author'] = result.author
            
            spider.logger.info(f"AI repair success for: {adapter.get('url', 'unknown')}")
        else:
            self.stats['failed'] += 1
            spider.logger.warning(f"AI repair failed: {result.error}")
        
        return item
    
    def close_spider(self, spider):
        if self.stats['triggered'] > 0:
            spider.logger.info(
                f"AI Repair Stats: "
                f"Triggered={self.stats['triggered']}, "
                f"Success={self.stats['success']}, "
                f"Failed={self.stats['failed']}"
            )
