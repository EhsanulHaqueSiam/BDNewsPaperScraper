# 📰 Bangladesh News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

**🔗 [View on Kaggle](https://www.kaggle.com/datasets/ehsanulhaque2111/bangladesh-news-articles)** | **📦 [Source Code](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)**

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Articles** | 17,520 |
| Total in Database | 600 |
| Added Today | 301 |
| Date Range | 2018-04-08 to Unknown |
| Newspapers | 14 |
| Categories | 48 |
| Last Updated | 2026-03-17 |

---

## 📰 Articles by Newspaper

| Newspaper | Articles | % |
|-----------|----------|---|
| Jago News 24 | 4,808 | 27.4% |
| The Daily Star | 2,935 | 16.8% |
| Rising BD | 2,467 | 14.1% |
| Daily Naya Diganta | 2,020 | 11.5% |
| Prothom Alo | 1,564 | 8.9% |
| The Business Standard | 1,373 | 7.8% |
| Dhaka Post | 973 | 5.6% |
| Jugantor | 785 | 4.5% |
| BD News 24 | 202 | 1.2% |
| Barta24 | 192 | 1.1% |
| BBC Bangla | 91 | 0.5% |
| Dhaka Tribune | 63 | 0.4% |
| Samakal | 41 | 0.2% |
| The Daily Ittefaq | 6 | 0.0% |

---

## 🏷️ Articles by Category

| Category | Articles | % |
|----------|----------|---|
| national | 3,422 | 19.5% |
| sports | 3,002 | 17.1% |
| politics | 2,413 | 13.8% |
| Bangladesh | 1,884 | 10.8% |
| bangladesh | 1,538 | 8.8% |
| economy | 1,448 | 8.3% |
| Sports | 1,358 | 7.8% |
| Business | 1,263 | 7.2% |
| জাতীয় | 221 | 1.3% |
| রাজনীতি | 145 | 0.8% |
| আন্তর্জাতিক | 141 | 0.8% |
| সারাদেশ | 98 | 0.6% |
| world | 96 | 0.5% |
| all | 91 | 0.5% |
| বিনোদন | 68 | 0.4% |
| *...and 33 more* | | |

---

## 📂 Available Files

| Format | File | Size | Best For |
|--------|------|------|----------|
| JSON | `articles.json` | 73.7 MB | Web apps, APIs, JavaScript |
| CSV | `articles.csv` | 68.1 MB | Excel, Google Sheets, pandas, R |
| Excel | `articles.xlsx` | 19.7 MB | Microsoft Excel, LibreOffice |
| Parquet | `articles.parquet` | 27.2 MB | Spark, Dask, big data analytics |
| SQLite | `database/news_articles.db` | - | SQL queries, local analysis |

---

## 🔬 Data Schema

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

## 🚀 Quick Start

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

## 📜 License

**CC0 1.0 Universal (Public Domain)** - Free to use for any purpose.

---

## 🙏 Citation

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
