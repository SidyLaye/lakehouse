#!/usr/bin/env python3
import sys, os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.types import Date

# === CONFIG POSTGRES À ADAPTER ===
DB_HOST     = "postgres"
DB_PORT     = "5432"
DB_NAME     = "mydb"
DB_USER     = "myuser"
DB_PASSWORD = "mysupersecret"
# =================================

def load_csv_to_postgres(csv_path, initial_date_str="2025-01-01"):
    # 1) Load CSV
    df_new = pd.read_csv(csv_path)

    # 2) Prepare table name + engine
    table_name = "transaction_data"
    url        = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine     = create_engine(url)
    inspector  = inspect(engine)

    # 3) If table does not exist, create it with situation_date AND
    #    immediately insert the first batch with the initial_date
    if not inspector.has_table(table_name):
        # 3a) Create empty table with only situation_date forced to Date()
        df_new.head(0).assign(situation_date=pd.to_datetime(initial_date_str)) \
                      .to_sql(
                        name=table_name,
                        con=engine,
                        index=False,
                        dtype={"situation_date": Date()},
                      )
        print(f"🆕 Table '{table_name}' created (with situation_date column).")

        # 3b) Insert initial rows with situation_date = initial_date
        df_new["situation_date"] = pd.to_datetime(initial_date_str).date()
        df_new.to_sql(
            name=table_name,
            con=engine,
            index=False,
            if_exists="append"
        )
        print(f"✅ Inserted {len(df_new)} rows with initial situation_date = {initial_date_str}.")
        return  # <-- important! skip the “update+append” path on first load

    # 4) Otherwise (table exists), make sure the column is there
    cols = [c["name"] for c in inspector.get_columns(table_name)]
    if "situation_date" not in cols:
        print(f"⚠️ Table '{table_name}' exists but has no situation_date → adding it…")
        with engine.begin() as conn:
            conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN situation_date DATE DEFAULT :d"),
                {"d": initial_date_str}
            )
        print("✔ situation_date column added with default initial date.")

    # 5) Increment ALL existing rows by 1 day
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE {table_name} SET situation_date = situation_date + INTERVAL '1 day'")
        )
    print("🆙 Incremented situation_date for all existing rows by 1 day.")

    # 6) Grab the new max date
    with engine.connect() as conn:
        maxd = conn.execute(
            text(f"SELECT MAX(situation_date) FROM {table_name}")
        ).scalar_one()
    print(f"New max(situation_date) in table: {maxd}")

    # 7) Stamp your incoming CSV with that date
    df_new["situation_date"] = maxd

    # 8) Append the new rows
    df_new.to_sql(
        name=table_name,
        con=engine,
        index=False,
        if_exists="append"
    )
    print(f"✅ Appended {len(df_new)} new rows with situation_date = {maxd}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db.py path/to/file.csv [YYYY-MM-DD]")
        sys.exit(1)
    csv_file     = sys.argv[1]
    initial_date = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"
    load_csv_to_postgres(csv_file, initial_date)
