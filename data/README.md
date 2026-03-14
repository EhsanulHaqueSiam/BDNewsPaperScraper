# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 16,631 |
| Total in Database | 546 |
| Added Today | 209 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 48 |
| Last Updated | 2026-03-14 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,561 | 27.4% |
| The Daily Star | 2,773 | 16.7% |
| Rising BD | 2,347 | 14.1% |
| Daily Naya Diganta | 1,896 | 11.4% |
| Prothom Alo | 1,522 | 9.2% |
| The Business Standard | 1,276 | 7.7% |
| Dhaka Post | 928 | 5.6% |
| Jugantor | 749 | 4.5% |
| Barta24 | 192 | 1.2% |
| BD News 24 | 186 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,229 | 19.4% |
| sports | 2,803 | 16.9% |
| politics | 2,348 | 14.1% |
| Bangladesh | 1,813 | 10.9% |
| bangladesh | 1,434 | 8.6% |
| economy | 1,369 | 8.2% |
| Sports | 1,302 | 7.8% |
| Business | 1,186 | 7.1% |
| জাতীয় | 216 | 1.3% |
| রাজনীতি | 145 | 0.9% |
| আন্তর্জাতিক | 132 | 0.8% |
| সারাদেশ | 96 | 0.6% |
| all | 91 | 0.5% |
| world | 89 | 0.5% |
| বিনোদন | 62 | 0.4% |
| *...and 33 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 70.0 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 64.7 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 18.7 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 25.8 MB | Spark, Dask, big data analytics |
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
