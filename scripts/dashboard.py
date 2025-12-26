#!/usr/bin/env python3
"""
Streamlit Dashboard for BD Newspaper Scraper
=============================================
A comprehensive web dashboard for visualizing scraped news data.

Run:
    streamlit run dashboard.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import re

import streamlit as st
import pandas as pd

# Optional imports for advanced features
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Page config
st.set_page_config(
    page_title="BD News Dashboard",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(ttl=300)
def load_data(days: int = 30) -> pd.DataFrame:
    """Load articles from database."""
    if not DB_PATH.exists():
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    df = pd.read_sql_query(
        """
        SELECT 
            id, headline, paper_name, category, url,
            publication_date, scraped_at,
            LENGTH(article) as article_length
        FROM articles 
        WHERE scraped_at >= ?
        ORDER BY scraped_at DESC
        """,
        conn,
        params=[cutoff]
    )
    conn.close()
    
    # Parse dates
    df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce')
    df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')
    df['date'] = df['scraped_at'].dt.date
    
    return df


@st.cache_data(ttl=300)
def get_total_stats() -> dict:
    """Get overall database statistics."""
    if not DB_PATH.exists():
        return {"total": 0, "papers": 0, "categories": 0}
    
    conn = sqlite3.connect(DB_PATH)
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "papers": conn.execute("SELECT COUNT(DISTINCT paper_name) FROM articles").fetchone()[0],
        "categories": conn.execute("SELECT COUNT(DISTINCT category) FROM articles WHERE category IS NOT NULL").fetchone()[0],
    }
    conn.close()
    return stats


def render_metrics(df: pd.DataFrame):
    """Render top metrics cards."""
    stats = get_total_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📰 Total Articles", f"{stats['total']:,}")
    
    with col2:
        st.metric("📊 Last 30 Days", f"{len(df):,}")
    
    with col3:
        st.metric("🗞️ Newspapers", stats['papers'])
    
    with col4:
        today_count = len(df[df['date'] == datetime.now().date()])
        st.metric("📅 Today", today_count)


def render_charts(df: pd.DataFrame):
    """Render visualization charts."""
    if df.empty:
        st.warning("No data available for visualization")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Articles by Newspaper")
        paper_counts = df['paper_name'].value_counts().head(15)
        
        if PLOTLY_AVAILABLE:
            fig = px.bar(
                x=paper_counts.values,
                y=paper_counts.index,
                orientation='h',
                labels={'x': 'Articles', 'y': 'Newspaper'},
                color=paper_counts.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(paper_counts)
    
    with col2:
        st.subheader("📈 Daily Article Trend")
        daily_counts = df.groupby('date').size().reset_index(name='count')
        
        if PLOTLY_AVAILABLE:
            fig = px.line(
                daily_counts,
                x='date',
                y='count',
                labels={'date': 'Date', 'count': 'Articles'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(daily_counts.set_index('date')['count'])
    
    # Category distribution
    if 'category' in df.columns and df['category'].notna().any():
        st.subheader("📁 Articles by Category")
        category_counts = df['category'].value_counts().head(10)
        
        if PLOTLY_AVAILABLE:
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def render_word_cloud(df: pd.DataFrame):
    """Generate and render word cloud from headlines."""
    st.subheader("☁️ Word Cloud from Headlines")
    
    if not WORDCLOUD_AVAILABLE:
        st.info("Install wordcloud: `pip install wordcloud matplotlib`")
        return
    
    if df.empty:
        st.warning("No data available")
        return
    
    # Combine headlines
    text = " ".join(df['headline'].dropna().tolist())
    
    # Remove common words
    stop_words = set(['the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is', 'are', 
                      'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                      'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'with', 'by', 'from', 'as', 'that', 'this', 'it', 'its', 'or', 'but',
                      'not', 'no', 'if', 'so', 'than', 'too', 'very', 'just', 'over', 'also'])
    
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='viridis',
        max_words=100,
        stopwords=stop_words
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)


def render_trending(df: pd.DataFrame):
    """Show trending topics/keywords."""
    st.subheader("🔥 Trending Keywords (Last 7 Days)")
    
    recent = df[df['scraped_at'] >= datetime.now() - timedelta(days=7)]
    
    if recent.empty:
        st.info("No recent articles to analyze")
        return
    
    # Extract words from headlines
    words = []
    for headline in recent['headline'].dropna():
        # Split and clean
        for word in re.findall(r'\b[A-Za-z]{4,}\b', headline):
            word = word.lower()
            if word not in ['this', 'that', 'with', 'from', 'have', 'been', 'will', 'would', 'could', 'their', 'about', 'says', 'said']:
                words.append(word)
    
    word_counts = Counter(words).most_common(20)
    
    if word_counts:
        keywords_df = pd.DataFrame(word_counts, columns=['Keyword', 'Count'])
        st.dataframe(keywords_df, use_container_width=True, hide_index=True)


def render_latest_headlines(df: pd.DataFrame):
    """Show latest headlines."""
    st.subheader("📰 Latest Headlines")
    
    for _, row in df.head(20).iterrows():
        with st.container():
            st.markdown(f"**[{row['headline'][:100]}...]({row['url']})**")
            st.caption(f"{row['paper_name']} | {row['category']} | {row['scraped_at']}")
            st.divider()


def render_search(df: pd.DataFrame):
    """Search articles."""
    st.subheader("🔍 Search Articles")
    
    query = st.text_input("Search headlines", placeholder="Enter keywords...")
    
    if query:
        results = df[df['headline'].str.contains(query, case=False, na=False)]
        st.write(f"Found {len(results)} articles")
        
        for _, row in results.head(20).iterrows():
            st.markdown(f"- [{row['headline'][:80]}...]({row['url']}) - *{row['paper_name']}*")


def main():
    st.title("🗞️ BD Newspaper Dashboard")
    st.caption("Real-time analytics for Bangladeshi news")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        days = st.slider("Data range (days)", 1, 90, 30)
        
        st.divider()
        st.markdown("### 📊 Quick Stats")
        stats = get_total_stats()
        st.markdown(f"- **Total Articles**: {stats['total']:,}")
        st.markdown(f"- **Newspapers**: {stats['papers']}")
        
        st.divider()
        st.markdown("### 🔗 Links")
        st.markdown("- [RSS Feeds](./feeds/index.html)")
        st.markdown("- [GitHub](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)")
    
    # Load data
    df = load_data(days)
    
    if df.empty:
        st.error("❌ No data found. Run some spiders first!")
        st.code("scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100")
        return
    
    # Render sections
    render_metrics(df)
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Charts", "☁️ Word Cloud", "🔥 Trending", "📰 Headlines", "🔍 Search"])
    
    with tab1:
        render_charts(df)
    
    with tab2:
        render_word_cloud(df)
    
    with tab3:
        render_trending(df)
    
    with tab4:
        render_latest_headlines(df)
    
    with tab5:
        render_search(df)
    
    # Footer
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data from {len(df)} articles")


if __name__ == "__main__":
    main()
