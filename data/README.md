# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 18,925 |
| Total in Database | 631 |
| Added Today | 117 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 71 |
| Last Updated | 2026-04-01 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,812 | 30.7% |
| The Daily Star | 2,935 | 15.5% |
| Rising BD | 2,467 | 13.0% |
| Daily Naya Diganta | 2,020 | 10.7% |
| Prothom Alo | 1,790 | 9.5% |
| The Business Standard | 1,373 | 7.3% |
| Dhaka Post | 973 | 5.1% |
| Jugantor | 960 | 5.1% |
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
| national | 3,701 | 19.6% |
| sports | 3,111 | 16.4% |
| politics | 2,428 | 12.8% |
| Bangladesh | 2,085 | 11.0% |
| bangladesh | 1,538 | 8.1% |
| economy | 1,503 | 7.9% |
| Sports | 1,383 | 7.3% |
| Business | 1,263 | 6.7% |
| জাতীয় | 254 | 1.3% |
| আন্তর্জাতিক | 191 | 1.0% |
| country | 176 | 0.9% |
| রাজনীতি | 153 | 0.8% |
| সারাদেশ | 125 | 0.7% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| *...and 56 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 81.1 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 75.0 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 21.7 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 29.9 MB | Spark, Dask, big data analytics |
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
