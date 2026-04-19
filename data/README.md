# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 20,766 |
| Total in Database | 624 |
| Added Today | 104 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 74 |
| Last Updated | 2026-04-19 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 7,105 | 34.2% |
| The Daily Star | 2,935 | 14.1% |
| Rising BD | 2,467 | 11.9% |
| Prothom Alo | 2,075 | 10.0% |
| Daily Naya Diganta | 2,020 | 9.7% |
| The Business Standard | 1,373 | 6.6% |
| Jugantor | 1,223 | 5.9% |
| Dhaka Post | 973 | 4.7% |
| BD News 24 | 202 | 1.0% |
| Barta24 | 192 | 0.9% |
| BBC Bangla | 91 | 0.4% |
| Dhaka Tribune | 63 | 0.3% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 4,025 | 19.4% |
| sports | 3,252 | 15.7% |
| politics | 2,476 | 11.9% |
| Bangladesh | 2,338 | 11.3% |
| economy | 1,634 | 7.9% |
| bangladesh | 1,538 | 7.4% |
| Sports | 1,415 | 6.8% |
| Business | 1,263 | 6.1% |
| country | 351 | 1.7% |
| জাতীয় | 305 | 1.5% |
| আন্তর্জাতিক | 250 | 1.2% |
| রাজনীতি | 163 | 0.8% |
| সারাদেশ | 144 | 0.7% |
| international | 144 | 0.7% |
| lifestyle | 128 | 0.6% |
| *...and 59 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 90.3 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 83.7 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 24.2 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 33.4 MB | Spark, Dask, big data analytics |
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
