# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 19,120 |
| Total in Database | 614 |
| Added Today | 95 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 72 |
| Last Updated | 2026-04-03 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,950 | 31.1% |
| The Daily Star | 2,935 | 15.4% |
| Rising BD | 2,467 | 12.9% |
| Daily Naya Diganta | 2,020 | 10.6% |
| Prothom Alo | 1,817 | 9.5% |
| The Business Standard | 1,373 | 7.2% |
| Jugantor | 990 | 5.2% |
| Dhaka Post | 973 | 5.1% |
| BD News 24 | 202 | 1.1% |
| Barta24 | 192 | 1.0% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.3% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,735 | 19.5% |
| sports | 3,126 | 16.3% |
| politics | 2,433 | 12.7% |
| Bangladesh | 2,110 | 11.0% |
| bangladesh | 1,538 | 8.0% |
| economy | 1,518 | 7.9% |
| Sports | 1,385 | 7.2% |
| Business | 1,263 | 6.6% |
| জাতীয় | 260 | 1.4% |
| আন্তর্জাতিক | 195 | 1.0% |
| country | 189 | 1.0% |
| রাজনীতি | 157 | 0.8% |
| সারাদেশ | 126 | 0.7% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| *...and 57 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 82.0 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 75.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 21.9 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 30.3 MB | Spark, Dask, big data analytics |
| SQLite | `database/news_articles.db` | - | SQL queries, local analysis |

---

## Data Schema

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

## Quick Start

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

## License

**CC0 1.0 Universal (Public Domain)** - Free to use for any purpose.

---

## Citation

```bibtex
@misc{ehsanul_haque_siam_2026,
    title={Bangladesh News Articles Dataset},
    url={https://www.kaggle.com/ds/9384161},
    DOI={10.34740/KAGGLE/DS/9384161},
    publisher={Kaggle},
    author={Ehsanul Haque Siam},
    year={2026}
}
```
