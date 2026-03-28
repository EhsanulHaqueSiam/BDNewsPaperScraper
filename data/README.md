# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 18,499 |
| Total in Database | 605 |
| Added Today | 84 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 70 |
| Last Updated | 2026-03-28 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,514 | 29.8% |
| The Daily Star | 2,935 | 15.9% |
| Rising BD | 2,467 | 13.3% |
| Daily Naya Diganta | 2,020 | 10.9% |
| Prothom Alo | 1,722 | 9.3% |
| The Business Standard | 1,373 | 7.4% |
| Dhaka Post | 973 | 5.3% |
| Jugantor | 900 | 4.9% |
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
| national | 3,614 | 19.5% |
| sports | 3,077 | 16.6% |
| politics | 2,421 | 13.1% |
| Bangladesh | 2,022 | 10.9% |
| bangladesh | 1,538 | 8.3% |
| economy | 1,477 | 8.0% |
| Sports | 1,378 | 7.4% |
| Business | 1,263 | 6.8% |
| জাতীয় | 241 | 1.3% |
| আন্তর্জাতিক | 176 | 1.0% |
| রাজনীতি | 152 | 0.8% |
| country | 140 | 0.8% |
| সারাদেশ | 114 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| *...and 55 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 78.8 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 72.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 21.1 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 29.1 MB | Spark, Dask, big data analytics |
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
