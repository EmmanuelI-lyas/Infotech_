import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

db_user = os.getenv("POSTGRES_USER", "postgres")
db_password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
db_host = os.getenv("POSTGRES_HOST", "postgres")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "titanic_db")
table_name = os.getenv("TITANIC_TABLE", "titanic")
csv_path = os.getenv("TITANIC_CSV_PATH", "/data/titanic/train.csv")

df = pd.read_csv(csv_path)

engine = create_engine(
    f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

df.to_sql(
    table_name,
    engine,
    if_exists="replace",
    index=False,
)

print(f"Loaded {len(df)} rows into '{table_name}' in database '{db_name}'.")