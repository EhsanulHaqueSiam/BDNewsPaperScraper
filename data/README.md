# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 18,333 |
| Total in Database | 609 |
| Added Today | 95 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 69 |
| Last Updated | 2026-03-26 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,392 | 29.4% |
| The Daily Star | 2,935 | 16.0% |
| Rising BD | 2,467 | 13.5% |
| Daily Naya Diganta | 2,020 | 11.0% |
| Prothom Alo | 1,702 | 9.3% |
| The Business Standard | 1,373 | 7.5% |
| Dhaka Post | 973 | 5.3% |
| Jugantor | 876 | 4.8% |
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
| national | 3,588 | 19.6% |
| sports | 3,060 | 16.7% |
| politics | 2,419 | 13.2% |
| Bangladesh | 2,002 | 10.9% |
| bangladesh | 1,538 | 8.4% |
| economy | 1,471 | 8.0% |
| Sports | 1,378 | 7.5% |
| Business | 1,263 | 6.9% |
| জাতীয় | 237 | 1.3% |
| আন্তর্জাতিক | 169 | 0.9% |
| রাজনীতি | 151 | 0.8% |
| country | 116 | 0.6% |
| সারাদেশ | 113 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| *...and 54 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 78.0 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 72.2 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.9 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 28.8 MB | Spark, Dask, big data analytics |
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
