# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 17,981 |
| Total in Database | 600 |
| Added Today | 80 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 64 |
| Last Updated | 2026-03-22 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,137 | 28.6% |
| The Daily Star | 2,935 | 16.3% |
| Rising BD | 2,467 | 13.7% |
| Daily Naya Diganta | 2,020 | 11.2% |
| Prothom Alo | 1,649 | 9.2% |
| The Business Standard | 1,373 | 7.6% |
| Dhaka Post | 973 | 5.4% |
| Jugantor | 832 | 4.6% |
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
| national | 3,515 | 19.5% |
| sports | 3,036 | 16.9% |
| politics | 2,415 | 13.4% |
| Bangladesh | 1,950 | 10.8% |
| bangladesh | 1,538 | 8.6% |
| economy | 1,457 | 8.1% |
| Sports | 1,377 | 7.7% |
| Business | 1,263 | 7.0% |
| জাতীয় | 227 | 1.3% |
| আন্তর্জাতিক | 157 | 0.9% |
| রাজনীতি | 147 | 0.8% |
| সারাদেশ | 111 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| বিনোদন | 71 | 0.4% |
| *...and 49 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 76.1 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 70.4 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.4 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 28.1 MB | Spark, Dask, big data analytics |
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
