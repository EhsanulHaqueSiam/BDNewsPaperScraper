# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 19,639 |
| Total in Database | 619 |
| Added Today | 107 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 72 |
| Last Updated | 2026-04-08 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 6,304 | 32.1% |
| The Daily Star | 2,935 | 14.9% |
| Rising BD | 2,467 | 12.6% |
| Daily Naya Diganta | 2,020 | 10.3% |
| Prothom Alo | 1,909 | 9.7% |
| The Business Standard | 1,373 | 7.0% |
| Jugantor | 1,063 | 5.4% |
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
| national | 3,817 | 19.4% |
| sports | 3,170 | 16.1% |
| politics | 2,446 | 12.5% |
| Bangladesh | 2,192 | 11.2% |
| economy | 1,553 | 7.9% |
| bangladesh | 1,538 | 7.8% |
| Sports | 1,395 | 7.1% |
| Business | 1,263 | 6.4% |
| জাতীয় | 274 | 1.4% |
| country | 242 | 1.2% |
| আন্তর্জাতিক | 213 | 1.1% |
| রাজনীতি | 157 | 0.8% |
| সারাদেশ | 133 | 0.7% |
| world | 96 | 0.5% |
| international | 95 | 0.5% |
| *...and 57 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 84.6 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 78.3 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 22.7 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 31.3 MB | Spark, Dask, big data analytics |
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
