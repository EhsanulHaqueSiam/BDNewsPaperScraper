# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 14,123 |
| Total in Database | 548 |
| Added Today | 286 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 44 |
| Last Updated | 2026-03-05 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 3,846 | 27.2% |
| The Daily Star | 2,313 | 16.4% |
| Rising BD | 2,011 | 14.2% |
| Daily Naya Diganta | 1,565 | 11.1% |
| Prothom Alo | 1,364 | 9.7% |
| The Business Standard | 1,026 | 7.3% |
| Dhaka Post | 797 | 5.6% |
| Jugantor | 650 | 4.6% |
| Barta24 | 192 | 1.4% |
| BD News 24 | 158 | 1.1% |
| BBC Bangla | 91 | 0.6% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.3% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 2,630 | 18.6% |
| sports | 2,363 | 16.7% |
| politics | 2,097 | 14.8% |
| Bangladesh | 1,572 | 11.1% |
| bangladesh | 1,173 | 8.3% |
| economy | 1,146 | 8.1% |
| Sports | 1,122 | 7.9% |
| Business | 989 | 7.0% |
| জাতীয় | 194 | 1.4% |
| রাজনীতি | 139 | 1.0% |
| আন্তর্জাতিক | 111 | 0.8% |
| all | 91 | 0.6% |
| সারাদেশ | 87 | 0.6% |
| world | 76 | 0.5% |
| বিনোদন | 56 | 0.4% |
| *...and 29 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 59.5 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 55.0 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 15.8 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 21.8 MB | Spark, Dask, big data analytics |
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
