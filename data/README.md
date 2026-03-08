# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 14,877 |
| Total in Database | 587 |
| Added Today | 235 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 46 |
| Last Updated | 2026-03-08 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,084 | 27.5% |
| The Daily Star | 2,459 | 16.5% |
| Rising BD | 2,120 | 14.3% |
| Daily Naya Diganta | 1,652 | 11.1% |
| Prothom Alo | 1,394 | 9.4% |
| The Business Standard | 1,100 | 7.4% |
| Dhaka Post | 837 | 5.6% |
| Jugantor | 673 | 4.5% |
| Barta24 | 192 | 1.3% |
| BD News 24 | 165 | 1.1% |
| BBC Bangla | 91 | 0.6% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.3% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 2,802 | 18.8% |
| sports | 2,515 | 16.9% |
| politics | 2,173 | 14.6% |
| Bangladesh | 1,625 | 10.9% |
| bangladesh | 1,251 | 8.4% |
| economy | 1,220 | 8.2% |
| Sports | 1,187 | 8.0% |
| Business | 1,047 | 7.0% |
| জাতীয় | 198 | 1.3% |
| রাজনীতি | 141 | 0.9% |
| আন্তর্জাতিক | 116 | 0.8% |
| all | 91 | 0.6% |
| সারাদেশ | 89 | 0.6% |
| world | 79 | 0.5% |
| বিনোদন | 57 | 0.4% |
| *...and 31 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 62.7 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 57.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 16.7 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 23.1 MB | Spark, Dask, big data analytics |
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
