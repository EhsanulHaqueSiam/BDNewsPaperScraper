import sqlite3
import pandas as pd

# SQLite database and table
db_file = "news_articles.db"
table_name = "articles"

# Output Excel file
excel_file = "news_articles.xlsx"

# Connect to SQLite and export to Excel
conn = sqlite3.connect(db_file)
df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
df.to_excel(excel_file, index=False)

print(f"Table {table_name} from {db_file} exported to {excel_file}")
