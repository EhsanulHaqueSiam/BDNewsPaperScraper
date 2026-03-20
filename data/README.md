# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 17,812 |
| Total in Database | 609 |
| Added Today | 97 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 63 |
| Last Updated | 2026-03-20 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,019 | 28.2% |
| The Daily Star | 2,935 | 16.5% |
| Rising BD | 2,467 | 13.9% |
| Daily Naya Diganta | 2,020 | 11.3% |
| Prothom Alo | 1,622 | 9.1% |
| The Business Standard | 1,373 | 7.7% |
| Dhaka Post | 973 | 5.5% |
| Jugantor | 808 | 4.5% |
| BD News 24 | 202 | 1.1% |
| Barta24 | 192 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,486 | 19.6% |
| sports | 3,026 | 17.0% |
| politics | 2,415 | 13.6% |
| Bangladesh | 1,925 | 10.8% |
| bangladesh | 1,538 | 8.6% |
| economy | 1,455 | 8.2% |
| Sports | 1,375 | 7.7% |
| Business | 1,263 | 7.1% |
| জাতীয় | 225 | 1.3% |
| আন্তর্জাতিক | 146 | 0.8% |
| রাজনীতি | 145 | 0.8% |
| সারাদেশ | 106 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| বিনোদন | 68 | 0.4% |
| *...and 48 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 75.3 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 69.6 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.1 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 27.8 MB | Spark, Dask, big data analytics |
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
