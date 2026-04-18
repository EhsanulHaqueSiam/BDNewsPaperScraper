# Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**[View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **[Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 20,662 |
| Total in Database | 628 |
| Added Today | 110 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 74 |
| Last Updated | 2026-04-18 |

---

## Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 7,031 | 34.0% |
| The Daily Star | 2,935 | 14.2% |
| Rising BD | 2,467 | 11.9% |
| Prothom Alo | 2,060 | 10.0% |
| Daily Naya Diganta | 2,020 | 9.8% |
| The Business Standard | 1,373 | 6.6% |
| Jugantor | 1,208 | 5.8% |
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
| national | 4,011 | 19.4% |
| sports | 3,245 | 15.7% |
| politics | 2,470 | 12.0% |
| Bangladesh | 2,326 | 11.3% |
| economy | 1,623 | 7.9% |
| bangladesh | 1,538 | 7.4% |
| Sports | 1,412 | 6.8% |
| Business | 1,263 | 6.1% |
| country | 342 | 1.7% |
| জাতীয় | 303 | 1.5% |
| আন্তর্জাতিক | 245 | 1.2% |
| রাজনীতি | 162 | 0.8% |
| সারাদেশ | 143 | 0.7% |
| international | 137 | 0.7% |
| lifestyle | 123 | 0.6% |
| *...and 59 more* | | |

---

## Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 89.8 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 83.2 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 24.1 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 33.2 MB | Spark, Dask, big data analytics |
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
