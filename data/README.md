# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 19,532 |
| Total in Database | 612 |
| Added Today | 99 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 72 |
| Last Updated | 2026-04-07 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 6,231 | 31.9% |
| The Daily Star | 2,935 | 15.0% |
| Rising BD | 2,467 | 12.6% |
| Daily Naya Diganta | 2,020 | 10.3% |
| Prothom Alo | 1,886 | 9.7% |
| The Business Standard | 1,373 | 7.0% |
| Jugantor | 1,052 | 5.4% |
| Dhaka Post | 973 | 5.0% |
| BD News 24 | 202 | 1.0% |
| Barta24 | 192 | 1.0% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.3% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,791 | 19.4% |
| sports | 3,162 | 16.2% |
| politics | 2,445 | 12.5% |
| Bangladesh | 2,173 | 11.1% |
| economy | 1,548 | 7.9% |
| bangladesh | 1,538 | 7.9% |
| Sports | 1,391 | 7.1% |
| Business | 1,263 | 6.5% |
| জাতীয় | 273 | 1.4% |
| country | 234 | 1.2% |
| আন্তর্জাতিক | 212 | 1.1% |
| রাজনীতি | 157 | 0.8% |
| সারাদেশ | 132 | 0.7% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| *...and 57 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 84.1 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 77.8 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 22.5 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 31.1 MB | Spark, Dask, big data analytics |
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
