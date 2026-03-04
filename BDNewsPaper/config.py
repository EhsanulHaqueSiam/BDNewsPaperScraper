"""
BDNewsPaper Configuration Module
================================
Centralized configuration for all spiders and the scraping framework.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import pytz


# Timezone configuration
DHAKA_TZ = pytz.timezone('Asia/Dhaka')

# Database configuration
DEFAULT_DB_PATH = 'news_articles.db'

# Default date range (last 30 days if not specified)
DEFAULT_START_DATE = '2024-01-01'

def get_default_end_date() -> str:
    """Get current date as default end date."""
    return datetime.now(DHAKA_TZ).strftime('%Y-%m-%d')


@dataclass
class SpiderConfig:
    """Configuration for a newspaper spider."""
    name: str
    paper_name: str
    allowed_domains: List[str]
    uses_api: bool = False
    supports_api_date_filter: bool = False
    supports_api_category_filter: bool = False
    supports_keyword_search: bool = False  # True if spider supports API-level search
    default_categories: List[str] = field(default_factory=list)
    language: str = 'English'  # 'English' or 'Bengali'


# Spider configurations
SPIDER_CONFIGS: Dict[str, SpiderConfig] = {
    'prothomalo': SpiderConfig(
        name='prothomalo',
        paper_name='ProthomAlo',
        allowed_domains=['en.prothomalo.com'],
        uses_api=True,
        supports_api_date_filter=True,
        supports_api_category_filter=True,
        supports_keyword_search=True,  # q parameter in advanced-search API
        default_categories=['Bangladesh', 'Sports', 'Opinion', 'Entertainment', 
                           'Youth', 'Environment', 'Science & Tech', 'Corporate'],
        language='English'
    ),
    'thedailystar': SpiderConfig(
        name='thedailystar',
        paper_name='The Daily Star',
        allowed_domains=['thedailystar.net'],
        uses_api=True,
        supports_api_date_filter=False,  # Date filter is client-side only
        supports_api_category_filter=True,
        supports_keyword_search=True,  # Google CSE at /search?t=
        default_categories=['bangladesh', 'investigative-stories', 'sports', 
                           'business', 'entertainment', 'star-multimedia', 'environment'],
        language='English'
    ),
    'dailysun': SpiderConfig(
        name='dailysun',
        paper_name='Daily Sun',
        allowed_domains=['www.daily-sun.com'],
        uses_api=True,
        supports_api_date_filter=True,
        supports_api_category_filter=True,
        default_categories=['national', 'economy', 'diplomacy', 'sports', 
                           'world', 'opinion', 'feature', 'sci-tech', 
                           'entertainment', 'corporate'],
        language='English'
    ),
    'bdpratidin': SpiderConfig(
        name='BDpratidin',
        paper_name='BD Pratidin',
        allowed_domains=['en.bd-pratidin.com'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        default_categories=['national', 'international', 'sports', 
                           'showbiz', 'economy', 'shuvosangho'],
        language='English'
    ),
    'ittefaq': SpiderConfig(
        name='ittefaq',
        paper_name='The Daily Ittefaq',
        allowed_domains=['ittefaq.com.bd', 'en.ittefaq.com.bd'],
        uses_api=True,
        supports_api_date_filter=False,  # Date filter is client-side only
        supports_api_category_filter=False,  # Uses fixed widget ID
        default_categories=['Bangladesh'],
        language='English'
    ),
    'bangladesh_today': SpiderConfig(
        name='bangladesh_today',
        paper_name='The Bangladesh Today',
        allowed_domains=['thebangladeshtoday.com'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        default_categories=['Bangladesh', 'Nationwide', 'International'],
        language='Bengali'  # Uses Bengali dates
    ),
    'dhakatribune': SpiderConfig(
        name='dhakatribune',
        paper_name='Dhaka Tribune',
        allowed_domains=['dhakatribune.com'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        supports_keyword_search=True,  # Has /search endpoint
        default_categories=['bangladesh', 'politics', 'business', 'sports',
                           'entertainment', 'opinion', 'world'],
        language='English'
    ),
    'financialexpress': SpiderConfig(
        name='financialexpress',
        paper_name='The Financial Express',
        allowed_domains=['thefinancialexpress.com.bd'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        default_categories=['national', 'economy', 'trade', 'stock',
                           'views-reviews', 'sports', 'world'],
        language='English'
    ),
    'newage': SpiderConfig(
        name='newage',
        paper_name='New Age',
        allowed_domains=['newagebd.net'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        default_categories=['politics', 'country', 'economy', 'business',
                           'sports', 'world', 'entertainment'],
        language='English'
    ),
    'bdnews24': SpiderConfig(
        name='bdnews24',
        paper_name='BD News 24',
        allowed_domains=['bdnews24.com'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=False,
        default_categories=['bangladesh', 'economy', 'sports', 'world',
                           'entertainment', 'opinion'],
        language='English'
    ),
    'theindependent': SpiderConfig(
        name='theindependent',
        paper_name='The Independent',
        allowed_domains=['theindependentbd.com'],
        uses_api=False,  # Uses RSS feed
        supports_api_date_filter=False,
        supports_api_category_filter=True,
        supports_keyword_search=True,
        default_categories=['politics', 'bangladesh', 'world', 'business',
                           'sports', 'entertainment', 'opinion', 'environment'],
        language='English'
    ),
    'observerbd': SpiderConfig(
        name='observerbd',
        paper_name='The Daily Observer',
        allowed_domains=['observerbd.com'],
        uses_api=False,
        supports_api_date_filter=False,
        supports_api_category_filter=True,  # Via category IDs
        default_categories=['national', 'international', 'business', 'sports',
                           'education', 'entertainment', 'health', 'opinion'],
        language='English'
    ),
}


# Scraping settings
DEFAULT_SETTINGS = {
    'DOWNLOAD_DELAY': 0.5,
    'RANDOMIZE_DOWNLOAD_DELAY': True,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
    'AUTOTHROTTLE_ENABLED': True,
    'AUTOTHROTTLE_START_DELAY': 0.25,
    'AUTOTHROTTLE_MAX_DELAY': 2.0,
    'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
}


# Validation settings
MIN_ARTICLE_LENGTH = 50  # Minimum characters for article body
MIN_HEADLINE_LENGTH = 5  # Minimum characters for headline


def get_spider_config(spider_name: str) -> Optional[SpiderConfig]:
    """Get configuration for a specific spider."""
    return SPIDER_CONFIGS.get(spider_name)


def list_available_spiders() -> List[str]:
    """List all available spider names."""
    return list(SPIDER_CONFIGS.keys())


def parse_date(date_str: str, end_of_day: bool = False) -> datetime:
    """
    Parse date string and localize to Dhaka timezone.
    
    Args:
        date_str: Date in YYYY-MM-DD format or 'today'
        end_of_day: If True, set time to 23:59:59
    
    Returns:
        Timezone-aware datetime object
    """
    if date_str.lower() == 'today':
        date_str = datetime.now(DHAKA_TZ).strftime('%Y-%m-%d')
    
    if len(date_str.split()) == 1:  # Only date provided
        time_part = "23:59:59" if end_of_day else "00:00:00"
        date_str = f"{date_str} {time_part}"
    
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    return DHAKA_TZ.localize(dt)
