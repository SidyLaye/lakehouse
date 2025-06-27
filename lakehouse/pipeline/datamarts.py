#!/usr/bin/env python3
# === Importations ===
import os
import sys
import signal
import psycopg2
from datetime import datetime

from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.sql.functions import to_date
from pyspark.storagelevel import StorageLevel

from signals import (
    DM_SIG_CLIENT_FEATURES,
    DM_SIG_CARD_FEATURES,
    DM_SIG_VELOCITY,
    DM_SIG_MCC_RISK,
    DM_SIG_TIME_DISTRIBUTION,
    DM_SIG_DONE,
    print_signal_mapping
)

# === CONFIGURATION ===
HIVE_DB    = "fraud_detection"
HIVE_TABLE = "preprocessed_full"

# Paramètres PostgreSQL (JDBC)
PG_HOST     = os.getenv("PG_HOST", "postgres")
PG_PORT     = os.getenv("PG_PORT", "5432")
PG_DB       = os.getenv("PG_NAME", "analytics")
PG_USER     = os.getenv("PG_USER", "grafana_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "grafana_pass")
PG_SCHEMA   = os.getenv("PG_SCHEMA", "public")

JDBC_URL = (
    f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"
    f"?user={PG_USER}&password={PG_PASSWORD}"
)

# Noms des tables datamarts
DM_CLIENT_FEATURES    = f"{PG_SCHEMA}.dm_client_features"
DM_CARD_FEATURES      = f"{PG_SCHEMA}.dm_card_features"
DM_VELOCITY_METRICS   = f"{PG_SCHEMA}.dm_client_velocity"
DM_MCC_RISK           = f"{PG_SCHEMA}.dm_mcc_fraud_risk"
DM_TIME_DISTRIBUTION  = f"{PG_SCHEMA}.dm_time_of_day_fraud"

# Mapping des signaux
FILE_SIGNALS = {
    "ClientFeatures":   DM_SIG_CLIENT_FEATURES,
    "CardFeatures":     DM_SIG_CARD_FEATURES,
    "Velocity":         DM_SIG_VELOCITY,
    "MccRisk":          DM_SIG_MCC_RISK,
    "TimeDistribution": DM_SIG_TIME_DISTRIBUTION
}
EXTRA_SIGNALS = {"Done": DM_SIG_DONE}

# Chemin du JAR JDBC Postgres
POSTGRES_JAR_PATH = os.path.join(os.path.dirname(__file__), "postgresql-42.7.5.jar")

# PID du watcher pour signaux inter-processus
WATCHER_PID = None

# === Initialisation Spark ===
def init_spark() -> SparkSession:
    return (
        SparkSession.builder
            .appName("datamarts_fraud_features")
            .config("spark.driver.memory", "8g")
            .config("spark.executor.memory", "8g")
            .config("spark.sql.warehouse.dir", "/user/hive/warehouse")
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
            .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minioadmin"))
            .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://localhost:9000"))
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
            .enableHiveSupport()
            .getOrCreate()
    )

# === Fonction d'écriture dans PostgreSQL et gestion des signaux ===
def write_pg(df, table: str, sig: int):
    """
    Crée la table si besoin, supprime l'existante, insère les données, puis envoie un signal.
    """
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, dbname=PG_DB,
            user=PG_USER, password=PG_PASSWORD
        )
        cur = conn.cursor()

        # Création conditionnelle de la table selon son nom
        if table.endswith("dm_client_features"):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    client_id         VARCHAR(128)    NOT NULL,
                    tx_count          BIGINT          NOT NULL,
                    avg_amount        DOUBLE PRECISION,
                    std_amount        DOUBLE PRECISION,
                    fraud_count       BIGINT,
                    drop_count        BIGINT,
                    unique_merchants  BIGINT,
                    fraud_rate        DOUBLE PRECISION,
                    drop_rate         DOUBLE PRECISION,
                    PRIMARY KEY (client_id)
                );
            """)
        elif table.endswith("dm_card_features"):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    tx_card_id     VARCHAR(128)    NOT NULL,
                    card_type      VARCHAR(64),
                    tx_count       BIGINT          NOT NULL,
                    fraud_count    BIGINT,
                    avg_amount     DOUBLE PRECISION,
                    drop_count     BIGINT,
                    fraud_rate     DOUBLE PRECISION,
                    drop_rate      DOUBLE PRECISION,
                    PRIMARY KEY (tx_card_id)
                );
            """)
        elif table.endswith("dm_client_velocity"):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    client_id       VARCHAR(128)     NOT NULL,
                    avg_daily_txn   DOUBLE PRECISION,
                    max_daily_txn   BIGINT,
                    PRIMARY KEY (client_id)
                );
            """)
        elif table.endswith("dm_mcc_fraud_risk"):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    mcc_code         VARCHAR(16)     NOT NULL,
                    mcc_description  VARCHAR(256),
                    tx_count         BIGINT,
                    fraud_count      BIGINT,
                    drop_count       BIGINT,
                    fraud_rate       DOUBLE PRECISION,
                    drop_rate        DOUBLE PRECISION,
                    PRIMARY KEY (mcc_code)
                );
            """)
        elif table.endswith("dm_time_of_day_fraud"):
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    hour            SMALLINT         NOT NULL,
                    tx_count        BIGINT,
                    fraud_count     BIGINT,
                    drop_count      BIGINT,
                    fraud_rate      DOUBLE PRECISION,
                    drop_rate       DOUBLE PRECISION,
                    PRIMARY KEY (hour)
                );
            """)
        else:
            # Si vous ajoutez d'autres tables, gérer ici
            pass

        conn.commit()

        # Suppression de la table existante (pour overwrite)
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()

        cur.close()
        conn.close()
        print(f"→ Table {table} prête")

    except Exception as e:
        print(f"[ERROR] Erreur sur la table {table} : {e}", file=sys.stderr)
        return

    # Écriture du DataFrame en mode append via JDBC
    df.write \
      .mode("append") \
      .jdbc(JDBC_URL, table, properties={"driver": "org.postgresql.Driver"})
    print(f"→ Données insérées dans {table}")

    # Envoi du signal uniquement au watcher
    global WATCHER_PID
    if WATCHER_PID is not None:
        os.kill(WATCHER_PID, sig)

# === Programme principal ===
def main():
    # Récupère le PID du watcher passé en argument
    global WATCHER_PID
    WATCHER_PID = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # Initialisation de Spark
    spark = init_spark()

    # Chargement de la table Hive et conversion de situation_date en DATE
    df_full = (
        spark
          .table(f"{HIVE_DB}.{HIVE_TABLE}")
          .persist(StorageLevel.MEMORY_AND_DISK)
    )

    # 5) Datamart “client features”
    client_feats = (
        df_full.groupBy("client_id")
               .agg(
                   F.count("transaction_id").alias("tx_count"),
                   F.avg("amount").alias("avg_amount"),
                   F.stddev("amount").alias("std_amount"),
                   F.sum(F.when(F.col("label") == 1, 1).otherwise(0)).alias("fraud_count"),
                   (F.count("transaction_id") - F.sum(F.when(F.col("label") == 1, 1).otherwise(0))).alias("drop_count"),
                   F.countDistinct("merchant_id").alias("unique_merchants")
               )
               .withColumn("fraud_rate", F.col("fraud_count") / F.col("tx_count"))
               .withColumn("drop_rate",  F.col("drop_count")  / F.col("tx_count"))
    )
    write_pg(client_feats, DM_CLIENT_FEATURES, FILE_SIGNALS["ClientFeatures"])

    # 6) Datamart “card features”
    card_feats = (
        df_full.groupBy("tx_card_id", "card_type")
               .agg(
                   F.count("transaction_id").alias("tx_count"),
                   F.sum("label").alias("fraud_count"),
                   F.avg("amount").alias("avg_amount"),
                   (F.count("transaction_id") - F.sum("label")).alias("drop_count")
               )
               .withColumn("fraud_rate", F.col("fraud_count") / F.col("tx_count"))
               .withColumn("drop_rate",  F.col("drop_count")  / F.col("tx_count"))
    )
    write_pg(card_feats, DM_CARD_FEATURES, FILE_SIGNALS["CardFeatures"])

    # 7) Datamart “velocity”
    velocity = (
        df_full.withColumn("date", to_date("timestamp_ts"))
               .groupBy("client_id", "date")
               .agg(F.count("transaction_id").alias("daily_txn"))
               .groupBy("client_id")
               .agg(
                   F.avg("daily_txn").alias("avg_daily_txn"),
                   F.max("daily_txn").alias("max_daily_txn")
               )
    )
    write_pg(velocity, DM_VELOCITY_METRICS, FILE_SIGNALS["Velocity"])

    # 8) Datamart “MCC risk”
    mcc_risk = (
        df_full.groupBy("mcc_code", "mcc_description")
               .agg(
                   F.count("transaction_id").alias("tx_count"),
                   F.sum("label").alias("fraud_count")
               )
               .withColumn("drop_count", F.col("tx_count") - F.col("fraud_count"))
               .withColumn("fraud_rate", F.col("fraud_count") / F.col("tx_count"))
               .withColumn("drop_rate", F.col("drop_count") / F.col("tx_count"))
    )
    write_pg(mcc_risk, DM_MCC_RISK, FILE_SIGNALS["MccRisk"])

    # 9) Datamart “time-of-day fraud distribution”
    time_dist = (
        df_full.withColumn("hour", F.hour("timestamp_ts"))
               .groupBy("hour")
               .agg(
                   F.count("transaction_id").alias("tx_count"),
                   F.sum("label").alias("fraud_count")
               )
               .withColumn("drop_count", F.col("tx_count") - F.col("fraud_count"))
               .withColumn("fraud_rate", F.col("fraud_count") / F.col("tx_count"))
               .withColumn("drop_rate", F.col("drop_count") / F.col("tx_count"))
    )
    write_pg(time_dist, DM_TIME_DISTRIBUTION, FILE_SIGNALS["TimeDistribution"])

    # Libération mémoire
    df_full.unpersist()

    # Signal “DONE” → on notifie uniquement le watcher
    if WATCHER_PID is not None:
        os.kill(WATCHER_PID, DM_SIG_DONE)

    spark.stop()

if __name__ == "__main__":
    main()
