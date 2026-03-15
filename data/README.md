# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 16,922 |
| Total in Database | 574 |
| Added Today | 291 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 48 |
| Last Updated | 2026-03-15 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,644 | 27.4% |
| The Daily Star | 2,829 | 16.7% |
| Rising BD | 2,380 | 14.1% |
| Daily Naya Diganta | 1,942 | 11.5% |
| Prothom Alo | 1,537 | 9.1% |
| The Business Standard | 1,303 | 7.7% |
| Dhaka Post | 942 | 5.6% |
| Jugantor | 761 | 4.5% |
| Barta24 | 192 | 1.1% |
| BD News 24 | 191 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,297 | 19.5% |
| sports | 2,861 | 16.9% |
| politics | 2,363 | 14.0% |
| Bangladesh | 1,837 | 10.9% |
| bangladesh | 1,463 | 8.6% |
| economy | 1,404 | 8.3% |
| Sports | 1,321 | 7.8% |
| Business | 1,214 | 7.2% |
| জাতীয় | 218 | 1.3% |
| রাজনীতি | 145 | 0.9% |
| আন্তর্জাতিক | 134 | 0.8% |
| সারাদেশ | 97 | 0.6% |
| all | 91 | 0.5% |
| world | 91 | 0.5% |
| বিনোদন | 65 | 0.4% |
| *...and 33 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 71.3 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 65.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 19.0 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 26.3 MB | Spark, Dask, big data analytics |
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
