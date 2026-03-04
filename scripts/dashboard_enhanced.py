#!/usr/bin/env python3
"""
BD News Dashboard - Premium Edition
====================================
A stunning, modern dashboard for Bangladeshi news analytics.

Run: streamlit run dashboard_enhanced.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import re
import json

import streamlit as st
import pandas as pd

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
BOOKMARKS_FILE = Path(__file__).parent / "bookmarks.json"

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="BD News Dashboard",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Premium CSS Styling - WCAG AA Compliant Contrast
# =============================================================================

st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main container */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Dark background - slightly lighter for better contrast */
    .stApp {
        background: linear-gradient(135deg, #121220 0%, #1e1e32 50%, #1a2744 100%);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* All text defaults - high contrast white */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label {
        color: #f8fafc !important;
    }
    
    /* Custom header */
    .dashboard-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.15) 100%);
        border: 1px solid rgba(167,139,250,0.3);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
    }
    
    .dashboard-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .dashboard-subtitle {
        color: #cbd5e1 !important;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Metric cards */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(45,45,75,0.95) 0%, rgba(55,55,90,0.95) 100%);
        border: 1px solid rgba(167,139,250,0.3);
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
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(129,140,248,0.2);
        border-color: rgba(167,139,250,0.5);
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0.25rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .metric-label {
        color: #e2e8f0 !important;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* News cards - improved contrast */
    .news-card {
        background: linear-gradient(135deg, rgba(45,45,75,0.9) 0%, rgba(55,55,90,0.9) 100%);
        border: 1px solid rgba(129,140,248,0.25);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .news-card:hover {
        transform: translateX(8px);
        border-color: rgba(167,139,250,0.6);
        box-shadow: 0 8px 32px rgba(129,140,248,0.15);
    }
    
    .news-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #818cf8, #c084fc);
        border-radius: 4px 0 0 4px;
    }
    
    .news-headline {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff !important;
        line-height: 1.5;
        margin-bottom: 0.75rem;
    }
    
    .news-headline a {
        color: #ffffff !important;
        text-decoration: none;
        transition: color 0.2s;
    }
    
    .news-headline a:hover {
        color: #c084fc !important;
        text-decoration: underline;
    }
    
    .news-meta {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }
    
    /* Meta tags - high contrast with distinct backgrounds */
    .meta-tag {
        background: rgba(129,140,248,0.25);
        color: #e0e7ff !important;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(129,140,248,0.3);
    }
    
    .meta-tag.paper {
        background: rgba(244,114,182,0.25);
        color: #fce7f3 !important;
        border-color: rgba(244,114,182,0.4);
    }
    
    .meta-tag.category {
        background: rgba(74,222,128,0.2);
        color: #dcfce7 !important;
        border-color: rgba(74,222,128,0.35);
    }
    
    .meta-tag.date {
        background: rgba(251,191,36,0.2);
        color: #fef3c7 !important;
        border-color: rgba(251,191,36,0.35);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(45,45,75,0.6);
        padding: 0.5rem;
        border-radius: 12px;
        border: 1px solid rgba(129,140,248,0.2);
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
        font-size: 1.5rem;
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
    
    /* Search box - high contrast */
    .stTextInput > div > div {
        background: rgba(45,45,75,0.9) !important;
        border: 2px solid rgba(129,140,248,0.4) !important;
        border-radius: 12px;
    }
    
    .stTextInput input {
        color: #ffffff !important;
        font-weight: 500;
    }
    
    .stTextInput input::placeholder {
        color: #a5b4fc !important;
    }
    
    .stTextInput > div > div:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 3px rgba(168,85,247,0.25) !important;
    }
    
    /* Select box */
    .stSelectbox > div > div {
        background: rgba(45,45,75,0.9) !important;
        border: 2px solid rgba(129,140,248,0.4) !important;
        border-radius: 12px;
    }
    
    .stSelectbox > div > div > div {
        color: #ffffff !important;
    }
    
    /* Multi-select */
    .stMultiSelect > div > div {
        background: rgba(45,45,75,0.9) !important;
        border: 2px solid rgba(129,140,248,0.4) !important;
        border-radius: 12px;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #121220 0%, #1e1e32 100%);
        border-right: 2px solid rgba(129,140,248,0.25);
    }
    
    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.5rem;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
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
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important;
    }
    
    /* DataFrame / Tables */
    .stDataFrame, .stTable {
        background: rgba(45,45,75,0.6) !important;
        border-radius: 12px;
        overflow: hidden;
    }
    
    .stDataFrame th {
        background: rgba(99,102,241,0.3) !important;
        color: #ffffff !important;
        font-weight: 700;
    }
    
    .stDataFrame td {
        color: #f1f5f9 !important;
        background: rgba(45,45,75,0.5) !important;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.4), transparent);
        margin: 2rem 0;
    }
    
    /* Info/Warning boxes */
    .stAlert {
        background: rgba(45,45,75,0.8) !important;
        border: 1px solid rgba(129,140,248,0.3) !important;
        border-radius: 12px;
    }
    
    .stAlert p {
        color: #e2e8f0 !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #cbd5e1 !important;
        padding: 2rem 0;
        font-size: 0.9rem;
    }
    
    .footer a {
        color: #c084fc !important;
        text-decoration: none;
        font-weight: 500;
    }
    
    .footer a:hover {
        text-decoration: underline;
    }
    
    /* Slider */
    .stSlider > div > div {
        color: #ffffff !important;
    }
    
    .stSlider label {
        color: #e2e8f0 !important;
    }
    
    /* Caption text */
    .stCaption, small {
        color: #cbd5e1 !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #f1f5f9 !important;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    .stMarkdown p, .stMarkdown li {
        color: #e2e8f0 !important;
    }
    
    .stMarkdown a {
        color: #c084fc !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(45,45,75,0.7) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(129,140,248,0.25) !important;
        color: #ffffff !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(35,35,60,0.8) !important;
        border: 1px solid rgba(129,140,248,0.2) !important;
        color: #e2e8f0 !important;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: rgba(34,197,94,0.2) !important;
        border: 1px solid rgba(34,197,94,0.4) !important;
        color: #dcfce7 !important;
    }
    
    .stError {
        background: rgba(239,68,68,0.2) !important;
        border: 1px solid rgba(239,68,68,0.4) !important;
        color: #fecaca !important;
    }
    
    .stWarning {
        background: rgba(251,191,36,0.2) !important;
        border: 1px solid rgba(251,191,36,0.4) !important;
        color: #fef3c7 !important;
    }
    
    .stInfo {
        background: rgba(99,102,241,0.2) !important;
        border: 1px solid rgba(99,102,241,0.4) !important;
        color: #e0e7ff !important;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .metric-container {
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
        .metric-value {
            font-size: 1.75rem;
        }
        .dashboard-title {
            font-size: 1.75rem;
        }
    }
    
    /* Plotly chart backgrounds */
    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session State
# =============================================================================

if 'bookmarks' not in st.session_state:
    if BOOKMARKS_FILE.exists():
        try:
            st.session_state.bookmarks = json.loads(BOOKMARKS_FILE.read_text())
        except:
            st.session_state.bookmarks = []
    else:
        st.session_state.bookmarks = []


# =============================================================================
# Data Loading
# =============================================================================

@st.cache_data(ttl=300)
def load_data(days: int = 30) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    df = pd.read_sql_query("""
        SELECT id, headline, paper_name, category, url, author,
               publication_date, scraped_at, LENGTH(article) as length
        FROM articles WHERE scraped_at >= ?
        ORDER BY scraped_at DESC
    """, conn, params=[cutoff])
    conn.close()
    
    df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce')
    df['date'] = df['scraped_at'].dt.date
    return df


@st.cache_data(ttl=300)
def get_papers() -> list:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    papers = [r[0] for r in conn.execute("SELECT DISTINCT paper_name FROM articles ORDER BY paper_name").fetchall()]
    conn.close()
    return papers


@st.cache_data(ttl=300)
def get_total_stats() -> dict:
    if not DB_PATH.exists():
        return {"total": 0, "papers": 0, "categories": 0, "today": 0}
    
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().date().isoformat()
    
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "papers": conn.execute("SELECT COUNT(DISTINCT paper_name) FROM articles").fetchone()[0],
        "categories": conn.execute("SELECT COUNT(DISTINCT category) FROM articles WHERE category IS NOT NULL").fetchone()[0],
        "today": conn.execute(f"SELECT COUNT(*) FROM articles WHERE date(scraped_at) = '{today}'").fetchone()[0],
    }
    conn.close()
    return stats


def save_bookmarks():
    BOOKMARKS_FILE.write_text(json.dumps(st.session_state.bookmarks))


def toggle_bookmark(article_id: int, headline: str, url: str):
    bookmark = {"id": article_id, "headline": headline, "url": url, "added": datetime.now().isoformat()}
    
    existing = [b for b in st.session_state.bookmarks if b['id'] == article_id]
    if existing:
        st.session_state.bookmarks = [b for b in st.session_state.bookmarks if b['id'] != article_id]
    else:
        st.session_state.bookmarks.append(bookmark)
    
    save_bookmarks()


# =============================================================================
# UI Components
# =============================================================================

def render_header():
    st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">🗞️ BD News Dashboard</h1>
        <p class="dashboard-subtitle">Real-time analytics for Bangladeshi news • Powered by AI</p>
    </div>
    """, unsafe_allow_html=True)


def render_metrics():
    stats = get_total_stats()
    
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-icon">📰</div>
            <div class="metric-value">{stats['total']:,}</div>
            <div class="metric-label">Total Articles</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">📅</div>
            <div class="metric-value">{stats['today']}</div>
            <div class="metric-label">Today</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🗞️</div>
            <div class="metric-value">{stats['papers']}</div>
            <div class="metric-label">Newspapers</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">⭐</div>
            <div class="metric-value">{len(st.session_state.bookmarks)}</div>
            <div class="metric-label">Bookmarks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_news_card(row, show_bookmark=True):
    """Render a beautiful news card."""
    headline = str(row['headline'])[:150]
    paper = row.get('paper_name', 'Unknown')
    category = row.get('category', 'General') or 'General'
    date = str(row.get('publication_date', ''))[:10] if row.get('publication_date') else 'Recent'
    
    st.markdown(f"""
    <div class="news-card">
        <div class="news-headline">
            <a href="{row['url']}" target="_blank">{headline}</a>
        </div>
        <div class="news-meta">
            <span class="meta-tag paper">📰 {paper}</span>
            <span class="meta-tag category">📁 {category}</span>
            <span class="meta-tag date">📅 {date}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_charts(df: pd.DataFrame):
    """Render beautiful charts with Plotly."""
    if df.empty or not PLOTLY_AVAILABLE:
        st.info("📊 Charts require data and Plotly. Run some spiders first!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="section-header">📊 Articles by Source</div>', unsafe_allow_html=True)
        paper_counts = df['paper_name'].value_counts().head(10)
        
        fig = go.Figure(go.Bar(
            x=paper_counts.values,
            y=paper_counts.index,
            orientation='h',
            marker=dict(
                color=paper_counts.values,
                colorscale=[[0, '#818cf8'], [0.5, '#c084fc'], [1, '#f472b6']],
            )
        ))
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
            yaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
            font=dict(family='Inter', color='#e2e8f0'),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown('<div class="section-header">📈 Daily Trend</div>', unsafe_allow_html=True)
        daily = df.groupby('date').size().reset_index(name='count')
        
        fig = go.Figure(go.Scatter(
            x=daily['date'],
            y=daily['count'],
            mode='lines+markers',
            line=dict(color='#c084fc', width=3),
            marker=dict(size=8, color='#f472b6'),
            fill='tozeroy',
            fillcolor='rgba(192, 132, 252, 0.15)',
        ))
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
            yaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
            font=dict(family='Inter', color='#e2e8f0'),
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Category breakdown
    if df['category'].notna().any():
        st.markdown('<div class="section-header">📁 Category Distribution</div>', unsafe_allow_html=True)
        cat_counts = df['category'].value_counts().head(8)
        
        fig = go.Figure(go.Pie(
            labels=cat_counts.index,
            values=cat_counts.values,
            hole=0.6,
            marker=dict(colors=['#818cf8', '#c084fc', '#f472b6', '#fb7185', '#fb923c', '#fbbf24', '#4ade80', '#22d3ee']),
            textfont=dict(color='#ffffff', size=14),
        ))
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#e2e8f0'),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(color='#e2e8f0')
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_word_cloud(df: pd.DataFrame):
    """Render a beautiful word cloud."""
    if not WORDCLOUD_AVAILABLE or df.empty:
        st.info("☁️ Install wordcloud: pip install wordcloud matplotlib")
        return
    
    text = " ".join(df['headline'].dropna().tolist())
    stop_words = set([
        'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall'
    ])
    
    wc = WordCloud(
        width=1200,
        height=600,
        background_color='#1e1e32',
        colormap='cool',
        max_words=100,
        stopwords=stop_words,
        contour_width=0,
        font_path=None,
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('#1e1e32')
    ax.set_facecolor('#1e1e32')
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig, use_container_width=True)


def render_comparison(df: pd.DataFrame):
    """Render newspaper comparison."""
    papers = get_papers()
    selected = st.multiselect(
        "Select newspapers to compare (2-4)",
        papers,
        max_selections=4,
        placeholder="Choose newspapers..."
    )
    
    if len(selected) >= 2:
        comparison_data = []
        for paper in selected:
            paper_df = df[df['paper_name'] == paper]
            comparison_data.append({
                "Newspaper": paper,
                "Articles": len(paper_df),
                "Categories": paper_df['category'].nunique(),
                "Avg Length": f"{int(paper_df['length'].mean()):,}" if not paper_df.empty else "0",
                "Latest": paper_df['scraped_at'].max().strftime("%Y-%m-%d %H:%M") if not paper_df.empty else "N/A"
            })
        
        st.dataframe(
            pd.DataFrame(comparison_data),
            use_container_width=True,
            hide_index=True,
        )
        
        if PLOTLY_AVAILABLE:
            cat_data = []
            for paper in selected:
                paper_df = df[df['paper_name'] == paper]
                for cat, count in paper_df['category'].value_counts().head(5).items():
                    if cat:
                        cat_data.append({"Newspaper": paper, "Category": cat, "Count": count})
            
            if cat_data:
                fig = px.bar(
                    pd.DataFrame(cat_data),
                    x="Category",
                    y="Count",
                    color="Newspaper",
                    barmode="group",
                    color_discrete_sequence=['#818cf8', '#c084fc', '#f472b6', '#fb7185'],
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=0, r=0, t=20, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
                    yaxis=dict(gridcolor='rgba(129,140,248,0.15)', color='#e2e8f0', tickfont=dict(color='#e2e8f0')),
                    font=dict(family='Inter', color='#e2e8f0'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#e2e8f0')),
                )
                st.plotly_chart(fig, use_container_width=True)


def render_bookmarks():
    """Render bookmarked articles."""
    if not st.session_state.bookmarks:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #cbd5e1;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⭐</div>
            <div style="font-size: 1.25rem; margin-bottom: 0.5rem; color: #e2e8f0;">No bookmarks yet</div>
            <div style="font-size: 0.9rem; color: #94a3b8;">Click the bookmark button on articles to save them</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    for bm in reversed(st.session_state.bookmarks[-20:]):
        col1, col2 = st.columns([9, 1])
        with col1:
            st.markdown(f"""
            <div class="news-card" style="margin-bottom: 0.5rem;">
                <div class="news-headline">
                    <a href="{bm['url']}" target="_blank">{bm['headline'][:100]}...</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("🗑️", key=f"del_{bm['id']}"):
                st.session_state.bookmarks = [b for b in st.session_state.bookmarks if b['id'] != bm['id']]
                save_bookmarks()
                st.rerun()


# =============================================================================
# Main Application
# =============================================================================

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <div style="font-size: 2rem;">🗞️</div>
            <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem;">BD News</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### ⚙️ Settings")
        days = st.slider("Date Range", 1, 90, 30, help="Number of days to analyze")
        
        st.divider()
        
        st.markdown("### 🔗 Quick Links")
        st.markdown("""
        - 📡 [REST API](/docs)
        - 📰 [RSS Feeds](./feeds)
        - 💾 [GitHub](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)
        """)
        
        st.divider()
        
        st.markdown("### 📊 Quick Stats")
        stats = get_total_stats()
        st.markdown(f"""
        - **Total**: {stats['total']:,} articles
        - **Sources**: {stats['papers']} newspapers
        - **Categories**: {stats['categories']}
        """)
    
    # Main content
    render_header()
    render_metrics()
    
    # Load data
    df = load_data(days)
    
    if df.empty:
        st.error("❌ No data available. Run some spiders first!")
        st.code("uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100", language="bash")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📰 Latest News",
        "📊 Analytics",
        "☁️ Word Cloud",
        "🔄 Compare",
        "⭐ Bookmarks",
        "🔍 Search"
    ])
    
    with tab1:
        st.markdown('<div class="section-header">📰 Latest Headlines</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            paper_filter = st.selectbox(
                "Filter by newspaper",
                ["All Newspapers"] + get_papers(),
                label_visibility="collapsed"
            )
        with col2:
            limit = st.selectbox("Show", [10, 20, 50], index=1, label_visibility="collapsed")
        
        filtered = df if paper_filter == "All Newspapers" else df[df['paper_name'] == paper_filter]
        
        for _, row in filtered.head(limit).iterrows():
            render_news_card(row)
    
    with tab2:
        render_charts(df)
    
    with tab3:
        st.markdown('<div class="section-header">☁️ Trending Topics</div>', unsafe_allow_html=True)
        render_word_cloud(df)
    
    with tab4:
        st.markdown('<div class="section-header">🔄 Compare Sources</div>', unsafe_allow_html=True)
        render_comparison(df)
    
    with tab5:
        st.markdown('<div class="section-header">⭐ Saved Articles</div>', unsafe_allow_html=True)
        render_bookmarks()
    
    with tab6:
        st.markdown('<div class="section-header">🔍 Search Articles</div>', unsafe_allow_html=True)
        query = st.text_input(
            "Search",
            placeholder="Enter keywords to search headlines...",
            label_visibility="collapsed"
        )
        
        if query:
            results = df[df['headline'].str.contains(query, case=False, na=False)]
            st.markdown(f"**Found {len(results)} articles matching '{query}'**")
            st.divider()
            
            for _, row in results.head(20).iterrows():
                render_news_card(row)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Made with ❤️ for Bangladeshi news analytics</p>
        <p><a href="https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper">GitHub</a> • 
        Updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
