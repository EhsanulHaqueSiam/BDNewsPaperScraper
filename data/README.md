# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 18,065 |
| Total in Database | 608 |
| Added Today | 84 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 67 |
| Last Updated | 2026-03-23 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,200 | 28.8% |
| The Daily Star | 2,935 | 16.2% |
| Rising BD | 2,467 | 13.7% |
| Daily Naya Diganta | 2,020 | 11.2% |
| Prothom Alo | 1,658 | 9.2% |
| The Business Standard | 1,373 | 7.6% |
| Dhaka Post | 973 | 5.4% |
| Jugantor | 844 | 4.7% |
| BD News 24 | 202 | 1.1% |
| Barta24 | 192 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.3% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,527 | 19.5% |
| sports | 3,042 | 16.8% |
| politics | 2,415 | 13.4% |
| Bangladesh | 1,959 | 10.8% |
| bangladesh | 1,538 | 8.5% |
| economy | 1,466 | 8.1% |
| Sports | 1,377 | 7.6% |
| Business | 1,263 | 7.0% |
| জাতীয় | 228 | 1.3% |
| আন্তর্জাতিক | 158 | 0.9% |
| রাজনীতি | 149 | 0.8% |
| সারাদেশ | 111 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| country | 75 | 0.4% |
| *...and 52 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 76.6 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 70.9 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.5 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 28.3 MB | Spark, Dask, big data analytics |
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
