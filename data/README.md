# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaquesiam/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 16,129 |
| Total in Database | 575 |
| Added Today | 339 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 47 |
| Last Updated | 2026-03-12 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,429 | 27.5% |
| The Daily Star | 2,686 | 16.7% |
| Rising BD | 2,289 | 14.2% |
| Daily Naya Diganta | 1,818 | 11.3% |
| Prothom Alo | 1,493 | 9.3% |
| The Business Standard | 1,227 | 7.6% |
| Dhaka Post | 896 | 5.6% |
| Jugantor | 718 | 4.5% |
| Barta24 | 192 | 1.2% |
| BD News 24 | 180 | 1.1% |
| BBC Bangla | 91 | 0.6% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.3% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,101 | 19.2% |
| sports | 2,738 | 17.0% |
| politics | 2,293 | 14.2% |
| Bangladesh | 1,764 | 10.9% |
| bangladesh | 1,382 | 8.6% |
| economy | 1,317 | 8.2% |
| Sports | 1,271 | 7.9% |
| Business | 1,150 | 7.1% |
| জাতীয় | 208 | 1.3% |
| রাজনীতি | 145 | 0.9% |
| আন্তর্জাতিক | 125 | 0.8% |
| সারাদেশ | 94 | 0.6% |
| all | 91 | 0.6% |
| world | 87 | 0.5% |
| বিনোদন | 60 | 0.4% |
| *...and 32 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 68.1 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 62.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 18.1 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 25.1 MB | Spark, Dask, big data analytics |
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
