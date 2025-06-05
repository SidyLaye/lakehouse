import os
import sys
import signal
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.sql.functions import to_date
from minio import Minio

from signals import (
    PREPROC_SIG_RAW,
    PREPROC_SIG_DB,
    PREPROC_SIG_DONE,
    print_signal_mapping
)

# === CONFIGURATION ===
MINIO_ENDPOINT   = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"

BUCKET      = "lakehouse"
PREFIX_PARQ = "datalake/raw_files"
PREFIX_DB   = "datalake/mydb"
PREFIX_H    = "warehouse"
HIVE_DB     = "fraud_detection"
HIVE_TABLE  = "preprocessed_full"

APP_NAME = "preprocessing.py"

# Map descriptive steps to their signals
FILE_SIGNALS = {
    "Raw loads complete": PREPROC_SIG_RAW,
}
EXTRA_SIGNALS = {
    "Database export": PREPROC_SIG_DB,
    "All done (full preprocessing)": PREPROC_SIG_DONE
}


def _parse_minio(endpoint):
    if "://" not in endpoint:
        endpoint = "http://" + endpoint
    p = urlparse(endpoint)
    return p.netloc, (p.scheme == "https")


def init_minio():
    netloc, secure = _parse_minio(MINIO_ENDPOINT)
    return Minio(
        netloc,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=secure
    )


def init_spark():
    return (
        SparkSession.builder
        .appName(APP_NAME)
        .config("spark.driver.memory", "10g")
        .config("spark.executor.memory", "10g")
        .config("spark.sql.warehouse.dir", f"s3a://{BUCKET}/{PREFIX_H}/")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .enableHiveSupport()
        .getOrCreate()
    )


def _drop_conflicts(left_df, right_df, join_keys):
    overlaps = set(left_df.columns) & set(right_df.columns) - set(join_keys)
    return right_df.drop(*overlaps) if overlaps else right_df


def _latest_parquet(client, prefix, fname):
    base = f"{prefix}/{fname}/"
    latest_obj, latest_ts = None, None
    for obj in client.list_objects(BUCKET, prefix=base, recursive=True):
        if obj.object_name.endswith(".parquet"):
            if latest_ts is None or obj.last_modified > latest_ts:
                latest_ts, latest_obj = obj.last_modified, obj.object_name
    if not latest_obj:
        raise RuntimeError(f"No Parquet found for {fname} under {prefix}")
    return f"s3a://{BUCKET}/{latest_obj}"


def task_db_load(spark, client, watcher_pid=None):
    pid = os.getpid()
    path = f"s3a://{BUCKET}/{PREFIX_DB}/"
    print(f"→ Loading DB parquet from {path}")
    df = spark.read.parquet(path)

    os.kill(pid, PREPROC_SIG_DB)
    if watcher_pid:
        os.kill(watcher_pid, PREPROC_SIG_DB)
    return df


def task_raw_loads(spark, client, watcher_pid=None):
    pid = os.getpid()

    cards    = spark.read.parquet(_latest_parquet(client, PREFIX_PARQ, "cards_data.csv"))
    users    = spark.read.parquet(_latest_parquet(client, PREFIX_PARQ, "users_data.csv"))
    mcc      = spark.read.parquet(_latest_parquet(client, PREFIX_PARQ, "mcc_codes.json"))
    raw_lbl  = spark.read.parquet(_latest_parquet(client, PREFIX_PARQ, "train_fraud_labels.json"))

    cards = cards.withColumnRenamed("id", "card_id")
    users = users.withColumnRenamed("id", "client_id")
    mcc   = mcc.withColumnRenamed("key", "mcc_code")\
               .withColumnRenamed("value", "mcc_description")

    os.kill(pid, PREPROC_SIG_RAW)
    if watcher_pid:
        os.kill(watcher_pid, PREPROC_SIG_RAW)

    return cards, users, mcc, raw_lbl


def clean_join_write(spark, db_df, cards, users, mcc, raw_lbl):
    # --- 1) Build tx DF and standardize transaction_id as Long ---
    tx = (
        db_df
        .withColumnRenamed("id", "transaction_id")
        .withColumnRenamed("client_id", "tx_client_id")
        .withColumnRenamed("card_id", "tx_card_id")
        .withColumnRenamed("mcc", "mcc_code")
        .withColumn("transaction_id", F.col("transaction_id").cast(T.LongType()))
        .withColumn("amount", F.regexp_replace("amount", "[$,]", "").cast(T.DoubleType()))
        .filter(F.col("amount") > 0)
        .withColumn("timestamp_ts", F.to_timestamp("date", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("hour", F.hour("timestamp_ts"))
        .withColumn(
            "merchant_state",
            F.when(F.col("merchant_state").isNull(), "ONLINE").otherwise(F.col("merchant_state"))
        )
        .withColumn(
            "errors",
            F.when(F.col("errors").isNull(), "no error").otherwise(F.col("errors"))
        )
    )

    # --- 2) Prepare & cast labels DF ---
    lbl2 = (
        raw_lbl
        .withColumnRenamed("id", "transaction_id")
        .withColumnRenamed("target", "raw_label")
        .withColumn("transaction_id", F.col("transaction_id").cast(T.LongType()))
        .withColumn(
            "raw_label",
            F.when(F.col("raw_label") == "Yes", 1)
             .when(F.col("raw_label") == "No",  0)
             .otherwise(None)
             .cast(T.IntegerType())
        )
    )

    # --- 3) Join transactions → labels (left to keep all tx; fill missing with 0) ---
    j = tx.join(lbl2, on="transaction_id", how="left")\
          .fillna({"raw_label": 0})

    # --- 4) Join in cards, users, mcc (same as before) ---
    cards_clean = cards.dropDuplicates(["card_id"])
    users_clean = users.dropDuplicates(["client_id"])\
                       .withColumnRenamed("client_id", "u_client_id")

    j = (
        j.join(
            _drop_conflicts(j, cards_clean, ["card_id"]),
            j.tx_card_id == cards_clean.card_id, "left"
        )
        .drop(cards_clean.card_id)
    )
    j = (
        j.join(
            _drop_conflicts(j, users_clean, ["u_client_id"]),
            j.tx_client_id == users_clean.u_client_id, "left"
        )
        .drop("u_client_id", "tx_client_id")
    )
    j = j.join(
        _drop_conflicts(j, mcc, ["mcc_code"]),
        on="mcc_code", how="left"
    )

    # --- 5) Final cleansing, ordering & write ---
    final = (
        j.drop("date")
         .withColumn("acct_open_date", to_date("acct_open_date", "MM/yyyy"))
         .withColumn("zip_code", F.format_string("%05d", F.col("zip").cast(T.IntegerType())))
         .drop("zip")
         .withColumn("credit_limit",      F.regexp_replace("credit_limit","[$,]","").cast(T.DoubleType()))
         .withColumn("per_capita_income", F.regexp_replace("per_capita_income","[$,]","").cast(T.DoubleType()))
         .withColumn("yearly_income",     F.regexp_replace("yearly_income","[$,]","").cast(T.DoubleType()))
         .withColumn("total_debt",        F.regexp_replace("total_debt","[$,]","").cast(T.DoubleType()))
         .withColumn("label", F.col("raw_label"))
         .drop("raw_label")
    )

    desired_order = [
        "transaction_id","timestamp_ts","amount","mcc_code","use_chip","merchant_id",
        "merchant_city","merchant_state","zip_code","errors","situation_date","tx_card_id",
        "client_id","card_brand","card_type","card_number","expires","cvv","has_chip",
        "num_cards_issued","credit_limit","acct_open_date","year_pin_last_changed","card_on_dark_web",
        "current_age","retirement_age","birth_year","birth_month","gender","address","latitude",
        "longitude","per_capita_income","yearly_income","total_debt","credit_score",
        "num_credit_cards","mcc_description","label"
    ]
    final = final.select(*[c for c in desired_order if c in final.columns])
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {HIVE_DB}")
    print(f"→ final count: {final.count()}")
    final.write.mode("overwrite").saveAsTable(f"{HIVE_DB}.{HIVE_TABLE}")
    print(f"⮑ Saved to Hive {HIVE_DB}.{HIVE_TABLE}")


def main():
    watcher_pid = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print_signal_mapping(
        file_signals=FILE_SIGNALS,
        extra_signals=EXTRA_SIGNALS,
        title="Preprocessing.py Signal Mapping"
    )

    def _sig_logger(name):
        def handler(signum, frame):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] 🔔 Received signal {signum} → {name}")
        return handler

    signal.signal(PREPROC_SIG_RAW,  _sig_logger("Raw loads complete"))
    signal.signal(PREPROC_SIG_DB,   _sig_logger("DB load complete"))
    signal.signal(PREPROC_SIG_DONE, _sig_logger("All done"))

    client = init_minio()
    spark  = init_spark()

    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_db  = ex.submit(task_db_load,  spark, client, watcher_pid)
        fut_raw = ex.submit(task_raw_loads, spark, client, watcher_pid)
        db_df, cards, users, mcc, raw_lbl = fut_db.result(), *fut_raw.result()

    clean_join_write(spark, db_df, cards, users, mcc, raw_lbl)

    os.kill(os.getpid(), PREPROC_SIG_DONE)
    if watcher_pid:
        os.kill(watcher_pid, PREPROC_SIG_DONE)

    spark.stop()


if __name__ == "__main__":
    main()
