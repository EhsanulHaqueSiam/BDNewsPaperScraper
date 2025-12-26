#!/usr/bin/env python3
"""
BD Newspaper Scraper - Web Interface
=====================================
A Streamlit-based GUI for controlling and monitoring the newspaper scrapers.

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

# Spider configurations
SPIDERS = {
    "prothomalo": {
        "name": "Prothom Alo",
        "paper_name": "Prothom Alo",
        "categories": ["bangladesh", "world", "business", "sports", "entertainment", "lifestyle", "tech"],
        "speed": "⚡ Fast (API)",
    },
    "dailysun": {
        "name": "Daily Sun",
        "paper_name": "Daily Sun",
        "categories": ["national", "international", "sports", "business", "entertainment"],
        "speed": "🔄 Medium (AJAX)",
    },
    "ittefaq": {
        "name": "Daily Ittefaq",
        "paper_name": "The Daily Ittefaq",
        "categories": ["Bangladesh", "International", "Sports", "Business", "Entertainment", "Opinion"],
        "speed": "🔄 Medium (AJAX)",
        "supports_search": True,
    },
    "BDpratidin": {
        "name": "BD Pratidin",
        "paper_name": "BD Pratidin",
        "categories": ["national", "international", "sports", "showbiz", "economy", "shuvosangho"],
        "speed": "🔄 Medium (HTML)",
    },
    "bangladesh_today": {
        "name": "Bangladesh Today",
        "paper_name": "The Bangladesh Today",
        "categories": ["national", "international", "sports", "business", "politics"],
        "speed": "🔄 Medium (HTML)",
    },
    "thedailystar": {
        "name": "The Daily Star",
        "paper_name": "The Daily Star",
        "categories": ["news", "bangladesh", "opinion", "business", "sports", "lifestyle"],
        "speed": "🐢 Slower (Large archive)",
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
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
        if not cursor.fetchone():
            return {"total": 0, "by_paper": {}, "date_range": ("N/A", "N/A")}
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        
        # By paper
        cursor.execute("""
            SELECT paper_name, COUNT(*) as count 
            FROM articles 
            GROUP BY paper_name 
            ORDER BY count DESC
        """)
        by_paper = dict(cursor.fetchall())
        
        # Date range
        cursor.execute("SELECT MIN(publication_date), MAX(publication_date) FROM articles")
        date_range = cursor.fetchone()
        
        conn.close()
        return {
            "total": total,
            "by_paper": by_paper,
            "date_range": date_range or ("N/A", "N/A")
        }
    except Exception as e:
        return {"total": 0, "by_paper": {}, "date_range": ("N/A", "N/A"), "error": str(e)}


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
        query = "SELECT id, paper_name, headline, publication_date, url, LENGTH(article) as content_length FROM articles WHERE 1=1"
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
    
    # Start process
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


# Sidebar - Scraper Controls
with st.sidebar:
    st.title("🕷️ Scraper Controls")
    
    # Spider selection
    st.subheader("📰 Select Newspapers")
    selected_spiders = []
    for spider_id, spider_info in SPIDERS.items():
        if st.checkbox(f"{spider_info['name']} {spider_info['speed']}", key=f"spider_{spider_id}"):
            selected_spiders.append(spider_id)
    
    st.divider()
    
    # Date range
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    st.divider()
    
    # Categories (show only if one spider selected)
    if len(selected_spiders) == 1:
        spider_id = selected_spiders[0]
        available_categories = SPIDERS[spider_id]["categories"]
        st.subheader("📂 Categories")
        selected_categories = st.multiselect(
            "Select categories",
            options=available_categories,
            default=[]
        )
    else:
        selected_categories = []
    
    # Limit
    st.subheader("⚙️ Settings")
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


# Main content area
st.title("📰 BD Newspaper Scraper")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Browse Articles", "📋 Scraping Log"])

with tab1:
    # Database stats
    stats = get_database_stats()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Articles", f"{stats['total']:,}")
    with col2:
        st.metric("Newspapers", len(stats['by_paper']))
    with col3:
        st.metric("Earliest Date", stats['date_range'][0][:10] if stats['date_range'][0] and stats['date_range'][0] != 'N/A' else "N/A")
    with col4:
        st.metric("Latest Date", stats['date_range'][1][:10] if stats['date_range'][1] and stats['date_range'][1] != 'N/A' else "N/A")
    
    st.divider()
    
    # Articles by newspaper chart
    if stats['by_paper']:
        st.subheader("📊 Articles by Newspaper")
        chart_data = pd.DataFrame({
            "Newspaper": list(stats['by_paper'].keys()),
            "Articles": list(stats['by_paper'].values())
        })
        st.bar_chart(chart_data.set_index("Newspaper"))
    else:
        st.info("No articles in database yet. Start scraping to collect news articles!")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Refresh Stats", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📥 Export to Excel", use_container_width=True):
            if stats['total'] > 0:
                try:
                    subprocess.run(["python", "toxlsx.py", "--output", "news_export.xlsx"], check=True)
                    st.success("Exported to news_export.xlsx!")
                except Exception as e:
                    st.error(f"Export failed: {e}")
            else:
                st.warning("No articles to export!")
    with col3:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.scraping_output = []
            st.success("Logs cleared!")

with tab2:
    st.subheader("🔍 Browse & Search Articles")
    
    # Search controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        search_query = st.text_input("🔎 Search", placeholder="Search headlines or content...")
    with col2:
        paper_options = ["All"] + list(stats['by_paper'].keys())
        paper_filter = st.selectbox("📰 Newspaper", options=paper_options)
    with col3:
        result_limit = st.selectbox("Results", options=[50, 100, 500, 1000], index=1)
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
        st.write(f"Found **{len(df)}** articles")
        
        # Display results
        for _, row in df.iterrows():
            with st.expander(f"📄 {row['headline'][:100]}..." if len(str(row['headline'])) > 100 else f"📄 {row['headline']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**Newspaper:** {row['paper_name']}")
                with col2:
                    st.write(f"**Date:** {row['publication_date']}")
                with col3:
                    st.write(f"**Length:** {row['content_length']:,} chars")
                
                if st.button("📖 Read Full Article", key=f"read_{row['id']}"):
                    article = get_article_content(row['id'])
                    if article:
                        st.markdown("---")
                        st.markdown(f"### {article['headline']}")
                        st.markdown(f"*{article['paper_name']} | {article['publication_date']}*")
                        st.markdown(article['article'])
                        st.link_button("🔗 Original Article", article['url'])
    else:
        st.info("No articles found. Adjust your filters or start scraping!")

with tab3:
    st.subheader("📋 Scraping Log")
    
    if st.session_state.scraping_active:
        st.warning("🔄 Scraping in progress...")
        
        # Run the spider
        if selected_spiders:
            progress_placeholder = st.empty()
            log_placeholder = st.empty()
            
            for spider_id in selected_spiders:
                st.info(f"Starting {SPIDERS[spider_id]['name']}...")
                
                process = run_spider(
                    spider_id,
                    start_date=str(start_date) if start_date else None,
                    end_date=str(end_date) if end_date else None,
                    categories=selected_categories if selected_categories else None,
                    limit=article_limit if article_limit > 0 else None
                )
                
                # Stream output
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    st.session_state.scraping_output.append(line.strip())
                    # Keep only last 100 lines
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
            st.info("No scraping activity yet. Use the sidebar to start scraping!")


# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>BD Newspaper Scraper • Made with ❤️ using Streamlit</small>
    </div>
    """,
    unsafe_allow_html=True
)
