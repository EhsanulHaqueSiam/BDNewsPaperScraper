# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 19,942 |
| Total in Database | 611 |
| Added Today | 90 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 72 |
| Last Updated | 2026-04-11 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 6,517 | 32.7% |
| The Daily Star | 2,935 | 14.7% |
| Rising BD | 2,467 | 12.4% |
| Daily Naya Diganta | 2,020 | 10.1% |
| Prothom Alo | 1,956 | 9.8% |
| The Business Standard | 1,373 | 6.9% |
| Jugantor | 1,106 | 5.5% |
| Dhaka Post | 973 | 4.9% |
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
| national | 3,863 | 19.4% |
| sports | 3,192 | 16.0% |
| politics | 2,454 | 12.3% |
| Bangladesh | 2,235 | 11.2% |
| economy | 1,576 | 7.9% |
| bangladesh | 1,538 | 7.7% |
| Sports | 1,399 | 7.0% |
| Business | 1,263 | 6.3% |
| জাতীয় | 282 | 1.4% |
| country | 270 | 1.4% |
| আন্তর্জাতিক | 225 | 1.1% |
| রাজনীতি | 159 | 0.8% |
| সারাদেশ | 137 | 0.7% |
| international | 108 | 0.5% |
| lifestyle | 103 | 0.5% |
| *...and 57 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 86.2 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 79.8 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 23.1 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 31.8 MB | Spark, Dask, big data analytics |
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
