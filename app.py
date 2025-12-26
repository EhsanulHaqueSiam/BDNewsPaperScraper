#!/usr/bin/env python3
"""
BD Newspaper Scraper - Web Interface (Premium Edition)
======================================================
A stunning Streamlit-based GUI for controlling and monitoring newspaper scrapers.

Run with: streamlit run app.py
"""

import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import os

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("Required packages not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "pandas"])
    import streamlit as st
    import pandas as pd

# Page config
st.set_page_config(
    page_title="BD Newspaper Scraper",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# Premium CSS Styling - WCAG AA Compliant High Contrast
# =============================================================================

st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles - Force high contrast text */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #f1f5f9 !important;
    }
    
    /* Main container */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Dark background - slightly lighter for contrast */
    .stApp {
        background: linear-gradient(135deg, #141428 0%, #1e1e38 50%, #1a2848 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Force all text to be visible */
    p, span, div, label, h1, h2, h3, h4, h5, h6 {
        color: #f1f5f9 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #141428 0%, #1e1e38 100%) !important;
        border-right: 2px solid rgba(129,140,248,0.3);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    
    /* Custom header */
    .app-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(236,72,153,0.2) 100%);
        border: 2px solid rgba(167,139,250,0.4);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
    }
    
    .app-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a5b4fc 0%, #d8b4fe 50%, #f9a8d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .app-subtitle {
        color: #e2e8f0 !important;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* Metric cards */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(50,50,85,0.95) 0%, rgba(60,60,100,0.95) 100%);
        border: 2px solid rgba(167,139,250,0.4);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #a5b4fc, #d8b4fe, #f9a8d4);
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(129,140,248,0.25);
        border-color: rgba(167,139,250,0.6);
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0.25rem 0;
        text-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    
    .metric-label {
        color: #e2e8f0 !important;
        font-size: 0.95rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(50,50,85,0.7);
        padding: 0.5rem;
        border-radius: 12px;
        border: 1px solid rgba(129,140,248,0.3);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #e2e8f0 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        color: #ffffff !important;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 1.5rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .section-header::after {
        content: '';
        flex: 1;
        height: 2px;
        background: linear-gradient(90deg, rgba(167,139,250,0.6), transparent);
    }
    
    /* Buttons - high visibility */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99,102,241,0.5) !important;
    }
    
    /* Input fields - high contrast */
    .stTextInput > div > div,
    .stSelectbox > div > div,
    .stNumberInput > div > div,
    .stMultiselect > div > div,
    .stDateInput > div > div {
        background: rgba(50,50,85,0.9) !important;
        border: 2px solid rgba(129,140,248,0.5) !important;
        border-radius: 10px;
    }
    
    .stTextInput input,
    .stNumberInput input {
        color: #ffffff !important;
        font-weight: 500;
    }
    
    .stTextInput input::placeholder {
        color: #c7d2fe !important;
        opacity: 1 !important;
    }
    
    .stTextInput > div > div:focus-within,
    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 3px rgba(168,85,247,0.3) !important;
    }
    
    /* Selectbox dropdown text */
    .stSelectbox > div > div > div {
        color: #ffffff !important;
    }
    
    /* Article card */
    .article-card {
        background: linear-gradient(135deg, rgba(50,50,85,0.9) 0%, rgba(60,60,100,0.9) 100%);
        border: 2px solid rgba(129,140,248,0.3);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .article-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #818cf8, #c084fc);
        border-radius: 4px 0 0 4px;
    }
    
    .article-card:hover {
        transform: translateX(6px);
        border-color: rgba(167,139,250,0.6);
        box-shadow: 0 8px 24px rgba(129,140,248,0.2);
    }
    
    .article-headline {
        font-size: 1.05rem;
        font-weight: 600;
        color: #ffffff !important;
        margin-bottom: 0.5rem;
        line-height: 1.5;
    }
    
    .article-meta {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }
    
    .meta-badge {
        background: rgba(129,140,248,0.3);
        color: #e0e7ff !important;
        padding: 0.3rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(129,140,248,0.4);
    }
    
    .meta-badge.paper {
        background: rgba(244,114,182,0.3);
        color: #fce7f3 !important;
        border-color: rgba(244,114,182,0.5);
    }
    
    .meta-badge.date {
        background: rgba(74,222,128,0.25);
        color: #dcfce7 !important;
        border-color: rgba(74,222,128,0.4);
    }
    
    /* Checkbox label styling */
    .stCheckbox label {
        color: #f1f5f9 !important;
        font-weight: 500;
    }
    
    .stCheckbox label span {
        color: #f1f5f9 !important;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.5), transparent);
        margin: 1.5rem 0;
    }
    
    /* Code block */
    .stCodeBlock, pre, code {
        background: rgba(25,25,45,0.9) !important;
        border: 1px solid rgba(129,140,248,0.3);
        border-radius: 10px;
        color: #e2e8f0 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(50,50,85,0.8) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(129,140,248,0.3) !important;
        color: #ffffff !important;
    }
    
    .streamlit-expanderHeader p {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    .streamlit-expanderContent {
        background: rgba(40,40,70,0.9) !important;
        border: 1px solid rgba(129,140,248,0.25) !important;
        color: #e2e8f0 !important;
    }
    
    /* Alert boxes */
    .stSuccess {
        background: rgba(34,197,94,0.25) !important;
        border: 2px solid rgba(34,197,94,0.5) !important;
    }
    .stSuccess p { color: #dcfce7 !important; }
    
    .stError {
        background: rgba(239,68,68,0.25) !important;
        border: 2px solid rgba(239,68,68,0.5) !important;
    }
    .stError p { color: #fecaca !important; }
    
    .stWarning {
        background: rgba(251,191,36,0.25) !important;
        border: 2px solid rgba(251,191,36,0.5) !important;
    }
    .stWarning p { color: #fef3c7 !important; }
    
    .stInfo {
        background: rgba(99,102,241,0.25) !important;
        border: 2px solid rgba(99,102,241,0.5) !important;
    }
    .stInfo p { color: #e0e7ff !important; }
    
    /* Markdown content */
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li {
        color: #f1f5f9 !important;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    .stMarkdown a {
        color: #d8b4fe !important;
        font-weight: 500;
    }
    
    .stMarkdown a:hover {
        color: #f0abfc !important;
        text-decoration: underline;
    }
    
    /* Caption */
    .stCaption, small, .caption {
        color: #cbd5e1 !important;
    }
    
    /* Metric widget override */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #e2e8f0 !important;
    }
    
    /* DataFrame / Table */
    .stDataFrame th {
        background: rgba(99,102,241,0.4) !important;
        color: #ffffff !important;
        font-weight: 700;
    }
    
    .stDataFrame td {
        color: #f1f5f9 !important;
        background: rgba(50,50,85,0.6) !important;
    }
    
    /* Footer */
    .app-footer {
        text-align: center;
        color: #e2e8f0 !important;
        padding: 2rem 0;
        font-size: 0.9rem;
        margin-top: 2rem;
    }
    
    .app-footer a {
        color: #d8b4fe !important;
        text-decoration: none;
        font-weight: 500;
    }
    
    .app-footer a:hover {
        text-decoration: underline;
    }
    
    /* Sidebar specific elements */
    .sidebar-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
        border-bottom: 2px solid rgba(129,140,248,0.3);
    }
    
    .sidebar-header-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-header-title {
        font-weight: 700;
        font-size: 1.25rem;
        background: linear-gradient(135deg, #a5b4fc, #d8b4fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Slider */
    .stSlider label {
        color: #f1f5f9 !important;
    }
    
    .stSlider > div > div > div {
        color: #ffffff !important;
    }
    
    /* Number input label */
    .stNumberInput label {
        color: #f1f5f9 !important;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .metric-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
        .metric-value {
            font-size: 1.5rem;
        }
        .app-title {
            font-size: 1.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Spider configurations
SPIDERS = {
    "prothomalo": {
        "name": "Prothom Alo",
        "paper_name": "Prothom Alo",
        "categories": ["bangladesh", "world", "business", "sports", "entertainment", "lifestyle", "tech"],
        "speed": "⚡ Fast",
        "type": "API",
    },
    "dailysun": {
        "name": "Daily Sun",
        "paper_name": "Daily Sun",
        "categories": ["national", "international", "sports", "business", "entertainment"],
        "speed": "⚡ Fast",
        "type": "AJAX",
    },
    "ittefaq": {
        "name": "Daily Ittefaq",
        "paper_name": "The Daily Ittefaq",
        "categories": ["Bangladesh", "International", "Sports", "Business", "Entertainment", "Opinion"],
        "speed": "🔄 Medium",
        "type": "AJAX",
        "supports_search": True,
    },
    "BDpratidin": {
        "name": "BD Pratidin",
        "paper_name": "BD Pratidin",
        "categories": ["national", "international", "sports", "showbiz", "economy", "shuvosangho"],
        "speed": "🔄 Medium",
        "type": "HTML",
    },
    "bangladesh_today": {
        "name": "Bangladesh Today",
        "paper_name": "The Bangladesh Today",
        "categories": ["national", "international", "sports", "business", "politics"],
        "speed": "🔄 Medium",
        "type": "HTML",
    },
    "thedailystar": {
        "name": "The Daily Star",
        "paper_name": "The Daily Star",
        "categories": ["news", "bangladesh", "opinion", "business", "sports", "lifestyle"],
        "speed": "🐢 Slow",
        "type": "HTML",
    },
    "dhakatribune": {
        "name": "Dhaka Tribune",
        "paper_name": "Dhaka Tribune",
        "categories": ["bangladesh", "world", "business", "sports", "opinion"],
        "speed": "🔄 Medium",
        "type": "HTML",
    },
    "newage": {
        "name": "New Age",
        "paper_name": "New Age",
        "categories": ["national", "politics", "business", "sports", "opinion"],
        "speed": "🔄 Medium",
        "type": "HTML",
    },
}

DB_PATH = "news_articles.db"


def get_db_connection():
    """Get database connection."""
    if not Path(DB_PATH).exists():
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def get_database_stats() -> Dict:
    """Get overall database statistics."""
    conn = get_db_connection()
    if not conn:
        return {"total": 0, "by_paper": {}, "date_range": ("N/A", "N/A")}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
        if not cursor.fetchone():
            return {"total": 0, "by_paper": {}, "date_range": ("N/A", "N/A")}
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT paper_name, COUNT(*) as count 
            FROM articles 
            GROUP BY paper_name 
            ORDER BY count DESC
        """)
        by_paper = dict(cursor.fetchall())
        
        cursor.execute("SELECT MIN(publication_date), MAX(publication_date) FROM articles")
        date_range = cursor.fetchone()
        
        today = datetime.now().date().isoformat()
        cursor.execute(f"SELECT COUNT(*) FROM articles WHERE date(scraped_at) = '{today}'")
        today_count = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total": total,
            "by_paper": by_paper,
            "date_range": date_range or ("N/A", "N/A"),
            "today": today_count,
        }
    except Exception as e:
        return {"total": 0, "by_paper": {}, "date_range": ("N/A", "N/A"), "error": str(e), "today": 0}


def search_articles(
    paper_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> pd.DataFrame:
    """Search articles with filters."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = "SELECT id, paper_name, headline, publication_date, url, category, LENGTH(article) as content_length FROM articles WHERE 1=1"
        params = []
        
        if paper_filter and paper_filter != "All":
            query += " AND paper_name = ?"
            params.append(paper_filter)
        
        if search_query:
            query += " AND (headline LIKE ? OR article LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        if start_date:
            query += " AND publication_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND publication_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


def get_article_content(article_id: int) -> Dict:
    """Get full article content."""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT headline, article, paper_name, publication_date, url, scraped_at 
            FROM articles WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "headline": row[0],
                "article": row[1],
                "paper_name": row[2],
                "publication_date": row[3],
                "url": row[4],
                "scraped_at": row[5]
            }
        return {}
    except Exception:
        return {}


def run_spider(spider_name: str, start_date: str = None, end_date: str = None, 
               categories: List[str] = None, limit: int = None) -> subprocess.Popen:
    """Run a spider with given parameters."""
    cmd = ["uv", "run", "scrapy", "crawl", spider_name, "-L", "INFO"]
    
    if start_date:
        cmd.extend(["-a", f"start_date={start_date}"])
    if end_date:
        cmd.extend(["-a", f"end_date={end_date}"])
    if categories:
        cmd.extend(["-a", f"categories={','.join(categories)}"])
    if limit:
        cmd.extend(["-s", f"CLOSESPIDER_ITEMCOUNT={limit}"])
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return process


# Initialize session state
if "scraping_active" not in st.session_state:
    st.session_state.scraping_active = False
if "scraping_output" not in st.session_state:
    st.session_state.scraping_output = []
if "selected_article_id" not in st.session_state:
    st.session_state.selected_article_id = None


# =============================================================================
# Sidebar - Scraper Controls
# =============================================================================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <div class="sidebar-header-icon">🕷️</div>
        <div class="sidebar-header-title">Scraper Controls</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Spider selection
    st.markdown("### 📰 Select Newspapers")
    selected_spiders = []
    
    for spider_id, spider_info in SPIDERS.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.checkbox(spider_info['name'], key=f"spider_{spider_id}"):
                selected_spiders.append(spider_id)
        with col2:
            st.caption(spider_info['speed'])
    
    st.divider()
    
    # Date range
    st.markdown("### 📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End", value=date.today())
    
    st.divider()
    
    # Categories
    if len(selected_spiders) == 1:
        spider_id = selected_spiders[0]
        available_categories = SPIDERS[spider_id]["categories"]
        st.markdown("### 📂 Categories")
        selected_categories = st.multiselect(
            "Select categories",
            options=available_categories,
            default=[],
            label_visibility="collapsed"
        )
    else:
        selected_categories = []
    
    # Limit
    st.markdown("### ⚙️ Settings")
    article_limit = st.number_input("Article Limit (0 = unlimited)", min_value=0, value=100, step=10)
    
    st.divider()
    
    # Start button
    if st.button("🚀 Start Scraping", type="primary", disabled=st.session_state.scraping_active, use_container_width=True):
        if not selected_spiders:
            st.error("Please select at least one newspaper!")
        else:
            st.session_state.scraping_active = True
            st.session_state.scraping_output = []
            st.rerun()
    
    if st.session_state.scraping_active:
        if st.button("🛑 Stop Scraping", type="secondary", use_container_width=True):
            st.session_state.scraping_active = False
            st.rerun()


# =============================================================================
# Main Content Area
# =============================================================================

# Header
st.markdown("""
<div class="app-header">
    <h1 class="app-title">📰 BD Newspaper Scraper</h1>
    <p class="app-subtitle">Collect and analyze news from 75+ Bangladeshi sources • Powered by Scrapy</p>
</div>
""", unsafe_allow_html=True)

# Stats
stats = get_database_stats()

# Metrics
st.markdown(f"""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-icon">📰</div>
        <div class="metric-value">{stats['total']:,}</div>
        <div class="metric-label">Total Articles</div>
    </div>
    <div class="metric-card">
        <div class="metric-icon">📅</div>
        <div class="metric-value">{stats.get('today', 0)}</div>
        <div class="metric-label">Today</div>
    </div>
    <div class="metric-card">
        <div class="metric-icon">🗞️</div>
        <div class="metric-value">{len(stats['by_paper'])}</div>
        <div class="metric-label">Newspapers</div>
    </div>
    <div class="metric-card">
        <div class="metric-icon">🕷️</div>
        <div class="metric-value">{len(SPIDERS)}</div>
        <div class="metric-label">Active Spiders</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Browse Articles", "📋 Scraping Log"])

with tab1:
    st.markdown('<div class="section-header">📊 Articles by Newspaper</div>', unsafe_allow_html=True)
    
    if stats['by_paper']:
        chart_data = pd.DataFrame({
            "Newspaper": list(stats['by_paper'].keys()),
            "Articles": list(stats['by_paper'].values())
        })
        st.bar_chart(chart_data.set_index("Newspaper"), color="#a855f7")
    else:
        st.info("📭 No articles in database yet. Start scraping to collect news!")
    
    # Quick actions
    st.markdown('<div class="section-header">⚡ Quick Actions</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📥 Export Excel", use_container_width=True):
            if stats['total'] > 0:
                try:
                    subprocess.run(["python", "scripts/toxlsx.py", "--output", "news_export.xlsx"], check=True)
                    st.success("✅ Exported!")
                except Exception as e:
                    st.error(f"❌ Failed: {e}")
    with col3:
        if st.button("📰 RSS Feeds", use_container_width=True):
            try:
                subprocess.run(["python", "scripts/rss_feed.py", "--all"], check=True)
                st.success("✅ Feeds generated!")
            except Exception as e:
                st.error(f"❌ Failed: {e}")
    with col4:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.scraping_output = []
            st.success("✅ Cleared!")

with tab2:
    st.markdown('<div class="section-header">🔍 Browse & Search Articles</div>', unsafe_allow_html=True)
    
    # Search controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        search_query = st.text_input("🔎 Search", placeholder="Search headlines...", label_visibility="collapsed")
    with col2:
        paper_options = ["All"] + list(stats['by_paper'].keys())
        paper_filter = st.selectbox("📰 Newspaper", options=paper_options, label_visibility="collapsed")
    with col3:
        result_limit = st.selectbox("Results", options=[25, 50, 100, 500], index=1, label_visibility="collapsed")
    with col4:
        search_btn = st.button("Search", type="primary", use_container_width=True)
    
    # Date filter
    col1, col2 = st.columns(2)
    with col1:
        filter_start = st.date_input("From", value=None, key="filter_start")
    with col2:
        filter_end = st.date_input("To", value=None, key="filter_end")
    
    # Results
    df = search_articles(
        paper_filter=paper_filter if paper_filter != "All" else None,
        search_query=search_query if search_query else None,
        start_date=str(filter_start) if filter_start else None,
        end_date=str(filter_end) if filter_end else None,
        limit=result_limit
    )
    
    if not df.empty:
        st.markdown(f"**Found {len(df)} articles**")
        st.divider()
        
        for _, row in df.iterrows():
            headline = str(row['headline'])[:120]
            paper = row.get('paper_name', 'Unknown')
            pub_date = str(row.get('publication_date', ''))[:10]
            category = row.get('category', '') or 'General'
            
            st.markdown(f"""
            <div class="article-card">
                <div class="article-headline">{headline}{'...' if len(str(row['headline'])) > 120 else ''}</div>
                <div class="article-meta">
                    <span class="meta-badge paper">📰 {paper}</span>
                    <span class="meta-badge">📁 {category}</span>
                    <span class="meta-badge date">📅 {pub_date}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📖 Read Full Article"):
                article = get_article_content(row['id'])
                if article:
                    st.markdown(f"### {article['headline']}")
                    st.caption(f"*{article['paper_name']} | {article['publication_date']}*")
                    st.markdown(article['article'])
                    st.link_button("🔗 Original Article", article['url'])
    else:
        st.info("📭 No articles found. Adjust your filters or start scraping!")

with tab3:
    st.markdown('<div class="section-header">📋 Scraping Log</div>', unsafe_allow_html=True)
    
    if st.session_state.scraping_active:
        st.warning("🔄 Scraping in progress...")
        
        if selected_spiders:
            progress_placeholder = st.empty()
            log_placeholder = st.empty()
            
            for spider_id in selected_spiders:
                st.info(f"🕷️ Starting {SPIDERS[spider_id]['name']}...")
                
                process = run_spider(
                    spider_id,
                    start_date=str(start_date) if start_date else None,
                    end_date=str(end_date) if end_date else None,
                    categories=selected_categories if selected_categories else None,
                    limit=article_limit if article_limit > 0 else None
                )
                
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    st.session_state.scraping_output.append(line.strip())
                    if len(st.session_state.scraping_output) > 100:
                        st.session_state.scraping_output = st.session_state.scraping_output[-100:]
                    log_placeholder.code('\n'.join(st.session_state.scraping_output[-20:]))
                
                process.wait()
                
                if process.returncode == 0:
                    st.success(f"✅ {SPIDERS[spider_id]['name']} completed!")
                else:
                    st.error(f"❌ {SPIDERS[spider_id]['name']} failed!")
            
            st.session_state.scraping_active = False
            st.rerun()
    else:
        if st.session_state.scraping_output:
            st.code('\n'.join(st.session_state.scraping_output[-50:]))
        else:
            st.info("🕷️ No scraping activity yet. Use the sidebar to start scraping!")


# Footer
st.markdown("""
<div class="app-footer">
    <p>Made with ❤️ for Bangladeshi news analytics</p>
    <p><a href="https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper">GitHub</a> • BD Newspaper Scraper</p>
</div>
""", unsafe_allow_html=True)
