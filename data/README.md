# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 17,219 |
| Total in Database | 581 |
| Added Today | 297 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 48 |
| Last Updated | 2026-03-16 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,729 | 27.5% |
| The Daily Star | 2,881 | 16.7% |
| Rising BD | 2,421 | 14.1% |
| Daily Naya Diganta | 1,980 | 11.5% |
| Prothom Alo | 1,549 | 9.0% |
| The Business Standard | 1,338 | 7.8% |
| Dhaka Post | 959 | 5.6% |
| Jugantor | 774 | 4.5% |
| BD News 24 | 195 | 1.1% |
| Barta24 | 192 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,367 | 19.6% |
| sports | 2,931 | 17.0% |
| politics | 2,377 | 13.8% |
| Bangladesh | 1,859 | 10.8% |
| bangladesh | 1,501 | 8.7% |
| economy | 1,431 | 8.3% |
| Sports | 1,338 | 7.8% |
| Business | 1,239 | 7.2% |
| জাতীয় | 220 | 1.3% |
| রাজনীতি | 145 | 0.8% |
| আন্তর্জাতিক | 138 | 0.8% |
| সারাদেশ | 98 | 0.6% |
| world | 92 | 0.5% |
| all | 91 | 0.5% |
| বিনোদন | 66 | 0.4% |
| *...and 33 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 72.5 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 67.0 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 19.3 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 26.7 MB | Spark, Dask, big data analytics |
| SQLite | `database/news_articles.db` | - | SQL queries, local analysis |

---

## 🔬 Data Schema

| Column | Type | Description |
|--------|------|-------------|
| `headline` | string | Article title/headline |
| `sub_title` | string | Article subtitle (may be null) |
| `article_body` | string | Full article text content |
| `url` | string | Original article URL |
| `publication_date` | datetime | When the article was published |
| `category` | string | News category |
| `paper_name` | string | Source newspaper name |
| `scraped_at` | datetime | When scraped |

---

## 🚀 Quick Start

```python
import pandas as pd

# Load data (choose your preferred format)
df = pd.read_parquet('articles.parquet')  # Fastest
# df = pd.read_csv('articles.csv')        # Universal
# df = pd.read_json('articles.json')      # JSON

print(f'Total articles: {len(df):,}')
print(df['paper_name'].value_counts().head(10))
```

---

## 📜 License

**CC0 1.0 Universal (Public Domain)** - Free to use for any purpose.

---

## 🙏 Citation

```
Ehsanul Haque Siam. (2026). Bangladesh News Articles Dataset.
Kaggle. https://doi.org/10.34740/KAGGLE/DS/9384161
```
