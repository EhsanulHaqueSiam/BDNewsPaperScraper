# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 18,144 |
| Total in Database | 602 |
| Added Today | 79 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 68 |
| Last Updated | 2026-03-24 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 5,258 | 29.0% |
| The Daily Star | 2,935 | 16.2% |
| Rising BD | 2,467 | 13.6% |
| Daily Naya Diganta | 2,020 | 11.1% |
| Prothom Alo | 1,668 | 9.2% |
| The Business Standard | 1,373 | 7.6% |
| Dhaka Post | 973 | 5.4% |
| Jugantor | 855 | 4.7% |
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
| national | 3,543 | 19.5% |
| sports | 3,049 | 16.8% |
| politics | 2,415 | 13.3% |
| Bangladesh | 1,968 | 10.8% |
| bangladesh | 1,538 | 8.5% |
| economy | 1,469 | 8.1% |
| Sports | 1,378 | 7.6% |
| Business | 1,263 | 7.0% |
| জাতীয় | 231 | 1.3% |
| আন্তর্জাতিক | 165 | 0.9% |
| রাজনীতি | 150 | 0.8% |
| সারাদেশ | 111 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| country | 87 | 0.5% |
| *...and 53 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 77.1 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 71.3 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 20.6 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 28.5 MB | Spark, Dask, big data analytics |
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
