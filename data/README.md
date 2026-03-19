# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 17,715 |
| Total in Database | 615 |
| Added Today | 92 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 63 |
| Last Updated | 2026-03-19 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,954 | 28.0% |
| The Daily Star | 2,935 | 16.6% |
| Rising BD | 2,467 | 13.9% |
| Daily Naya Diganta | 2,020 | 11.4% |
| Prothom Alo | 1,601 | 9.0% |
| The Business Standard | 1,373 | 7.8% |
| Dhaka Post | 973 | 5.5% |
| Jugantor | 797 | 4.5% |
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
| national | 3,469 | 19.6% |
| sports | 3,016 | 17.0% |
| politics | 2,415 | 13.6% |
| Bangladesh | 1,906 | 10.8% |
| bangladesh | 1,538 | 8.7% |
| economy | 1,454 | 8.2% |
| Sports | 1,373 | 7.8% |
| Business | 1,263 | 7.1% |
| জাতীয় | 222 | 1.3% |
| রাজনীতি | 145 | 0.8% |
| আন্তর্জাতিক | 144 | 0.8% |
| সারাদেশ | 102 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| বিনোদন | 68 | 0.4% |
| *...and 48 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 74.8 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 69.2 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.0 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 27.6 MB | Spark, Dask, big data analytics |
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
