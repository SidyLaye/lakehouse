import os
import sys
import signal
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from pyspark.sql import SparkSession
from minio import Minio
from minio.error import S3Error

from signals import (
    FEEDER_SIG_CARD,
    FEEDER_SIG_USER,
    FEEDER_SIG_MCC,
    FEEDER_SIG_LABELS,
    FEEDER_SIG_DB,
    FEEDER_SIG_DONE,
    print_signal_mapping
)

# === CONFIGURATION SECTION ===
API_BASE_URL      = "http://sources_api:9998"
MINIO_ENDPOINT    = "http://localhost:9000"
MINIO_ACCESS_KEY  = "minioadmin"
MINIO_SECRET_KEY  = "minioadmin"
S3_BUCKET         = "lakehouse"
S3_DATALAKE_PREFIX = "datalake"
INITIAL_DATE      = "2025-01-01"

PG_HOST     = "postgres"
PG_PORT     = "5432"
PG_NAME     = "mydb"
PG_USER     = "myuser"
PG_PASSWORD = "mysupersecret"
PG_TABLE    = "public.transaction_data"

SCRIPT_DIR          = os.path.dirname(os.path.realpath(__file__))
POSTGRES_JAR_PATH   = os.path.join(SCRIPT_DIR, "postgresql-42.7.5.jar")

MAX_WORKERS          = 8
DB_NUM_PARTITIONS    = 4
LOCAL_DB_PARQUET_DIR = "tmp/feeder_db"
LOCAL_RAW_TMP_DIR    = "tmp/feeder_raw_files"

# Mapping raw file names to signals
FILE_SIGNAL_MAP = {
    "cards_data.csv":          FEEDER_SIG_CARD,
    "users_data.csv":          FEEDER_SIG_USER,
    "mcc_codes.json":          FEEDER_SIG_MCC,
    "train_fraud_labels.json": FEEDER_SIG_LABELS,
}

# === Affichage de la cartographie des signaux ===
print_signal_mapping(
    file_signals=FILE_SIGNAL_MAP,
    extra_signals={
        "Database export": FEEDER_SIG_DB,
        "All done":        FEEDER_SIG_DONE
    },
    title="Feeder.py Signal Mapping"
)


def _parse_minio_endpoint(endpoint: str) -> (str, bool):
    """
    Transforme une URL (http://localhost:9000) en (host:port, secure?).
    """
    p = urlparse(endpoint)
    scheme = p.scheme.lower()
    secure = (scheme == "https")
    netloc = p.netloc
    return netloc, secure


def _init_minio_client():
    """
    Initialise et retourne un client MinIO.
    """
    endpoint_netloc, secure = _parse_minio_endpoint(MINIO_ENDPOINT)
    return Minio(
        endpoint_netloc,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=secure,
    )


def _init_spark() -> SparkSession:
    """
    Crée la SparkSession en incluant le JAR PostgreSQL et la configuration S3A pour MinIO.
    """
    if not os.path.isfile(POSTGRES_JAR_PATH):
        print(f"[FATAL] Cannot find JDBC JAR at '{POSTGRES_JAR_PATH}'.", file=sys.stderr)
        sys.exit(1)

    spark = (
        SparkSession
        .builder
        .appName("feeder.py")
        .config("spark.driver.memory", "8g")
        .config("spark.executor.memory", "8g")
        # Configuration pour écrire ensuite sur MinIO via s3a://
        .config("spark.hadoop.fs.s3a.impl",                          "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key",                    MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key",                    MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.endpoint",                      MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.path.style.access",             "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled",         "false")
        .getOrCreate()
    )
    return spark


def _get_next_ingestion_date_minio(minio_client: Minio, file_name: str) -> datetime.date:
    """
    Pour un nom de fichier brut (par ex. "cards_data.csv"), 
    parcourt MinIO et retourne la date (year=.../month=.../day=...) la plus récente,
    puis renvoie le lendemain. S’il n’y a rien, on retourne INITIAL_DATE.
    """
    prefix = f"{S3_DATALAKE_PREFIX}/raw_files/{file_name}/"
    found_dates = set()

    try:
        objects_iter = minio_client.list_objects(
            bucket_name=S3_BUCKET,
            prefix=prefix,
            recursive=True
        )
        for obj in objects_iter:
            key = obj.object_name
            parts = key.split('/')
            # On cherche un segment year=YYYY / month=MM / day=DD
            for i in range(len(parts) - 2):
                if (parts[i].startswith("year=") and
                    parts[i+1].startswith("month=") and
                    parts[i+2].startswith("day=")):
                    yyyy = parts[i].split("=", 1)[1]
                    mm   = parts[i+1].split("=", 1)[1]
                    dd   = parts[i+2].split("=", 1)[1]
                    try:
                        dt = datetime(int(yyyy), int(mm), int(dd)).date()
                        found_dates.add(dt)
                    except ValueError:
                        continue
    except S3Error:
        found_dates = set()

    if not found_dates:
        return datetime.strptime(INITIAL_DATE, "%Y-%m-%d").date()

    return max(found_dates) + timedelta(days=1)


def _upload_raw_parquet_minio(minio_client: Minio, local_parquet_path: str,
                             file_name: str, ingest_date: datetime.date):
    """
    Envoie sur MinIO le fichier local (brut ou déjà converti en .parquet),
    sous le préfixe « datalake/raw_files/<file_name>/year=YYYY/... ».
    """
    y, m, d = ingest_date.year, ingest_date.month, ingest_date.day
    parquet_filename = os.path.splitext(file_name)[0] + ".parquet"
    object_name = (
        f"{S3_DATALAKE_PREFIX}/raw_files/{file_name}/"
        f"year={y:04d}/month={m:02d}/day={d:02d}/{parquet_filename}"
    )
    try:
        print(f"[DEBUG] Upload RAW → bucket='{S3_BUCKET}', key='{object_name}'")  # Debug print
        minio_client.fput_object(S3_BUCKET, object_name, local_parquet_path)
    except S3Error as e:
        raise RuntimeError(f"MinIO upload failed for {parquet_filename} → {object_name}: {e}")


def process_single_file(file_name: str,
                        minio_client: Minio,
                        done_signal: int,
                        watcher_pid: int = None) -> None:
    """
    Télécharge via l’API un fichier raw (JSON ou CSV),    
    tente de le convertir en Parquet localement, puis l’upload sur MinIO.    
    Si la conversion échoue (ex. JSON au format spécial), on upload quand même le brut
    en le nommant «.parquet».
    """
    pid = os.getpid()
    try:
        download_url = urljoin(API_BASE_URL + "/", f"files/{file_name}")
        resp = requests.get(download_url, stream=True)
        resp.raise_for_status()

        os.makedirs(LOCAL_RAW_TMP_DIR, exist_ok=True)
        local_raw_path = os.path.join(LOCAL_RAW_TMP_DIR, file_name)
        with open(local_raw_path, "wb") as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)

        fname_no_ext, ext = os.path.splitext(file_name.lower())
        local_parquet_path = os.path.join(LOCAL_RAW_TMP_DIR, f"{fname_no_ext}.parquet")

        df_raw = None
        # Si c’est du JSON (sauf « train_fraud_labels.json » qu’on gère différemment)
        if ext == ".json":
            if file_name == "train_fraud_labels.json":
                df_raw = None
            else:
                try:
                    df_raw = pd.read_json(local_raw_path, lines=False)
                except ValueError:
                    df_raw = None

        # Si c’est du CSV
        elif ext == ".csv":
            try:
                df_raw = pd.read_csv(local_raw_path)
            except Exception:
                df_raw = None

        # Cas particulier : JSON imbriqué (ex : {"target": {"10649266": "No", ...}})
        if df_raw is None and ext == ".json":
            with open(local_raw_path, "r") as jf:
                parsed = json.load(jf)

            if (isinstance(parsed, dict)
                and len(parsed) == 1
                and isinstance(list(parsed.values())[0], dict)):
                top_key    = list(parsed.keys())[0]
                inner_dict = parsed[top_key]
                df_raw = pd.DataFrame(
                    list(inner_dict.items()),
                    columns=["id", top_key]
                )
            elif isinstance(parsed, dict):
                df_raw = pd.DataFrame(list(parsed.items()), columns=["key", "value"])
            else:
                raise ValueError(f"Unsupported JSON structure in '{file_name}'")

        # Si on n’a pas réussi à créer df_raw (ni CSV, ni JSON standard convertissable),
        # on upload quand même le brut sous un nom « .parquet » sans conversion.
        if df_raw is None:
            ingest_date = _get_next_ingestion_date_minio(minio_client, file_name)
            _upload_raw_parquet_minio(minio_client, local_raw_path, file_name, ingest_date)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] ⚠️ Skipped parquet conversion for unsupported format '{file_name}'. Uploaded raw as .parquet-named object.")
            os.kill(pid, done_signal)
            if watcher_pid:
                try:
                    os.kill(watcher_pid, done_signal)
                except ProcessLookupError:
                    print(f"[WARN] watcher PID {watcher_pid} not found; skipping external signal.", file=sys.stderr)
            return

        # Sinon, on a bien un DataFrame, on convertit en Parquet
        df_raw.head(99999).to_parquet(local_parquet_path, index=False)
        ingest_date = _get_next_ingestion_date_minio(minio_client, file_name)
        _upload_raw_parquet_minio(minio_client, local_parquet_path, file_name, ingest_date)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Finished converting & uploading: '{file_name}' → '{fname_no_ext}.parquet' (date={ingest_date.isoformat()})")
        os.kill(pid, done_signal)
        if watcher_pid:
            try:
                os.kill(watcher_pid, done_signal)
            except ProcessLookupError:
                print(f"[WARN] watcher PID {watcher_pid} not found; skipping external signal.", file=sys.stderr)

    except Exception as e:
        print(f"[ERROR][{file_name}]: {e}", file=sys.stderr)


def _get_next_situation_date_minio(minio_client: Minio) -> datetime.date:
    """
    Trouve la situation_date la plus récente dans MinIO sous datalake/mydb/situation_date=,
    puis retourne la date suivante (jour +1). Si aucune partition n'existe, retourne INITIAL_DATE.
    """
    prefix = f"{S3_DATALAKE_PREFIX}/{PG_NAME}/situation_date="
    found_dates = set()
    try:
        objects_iter = minio_client.list_objects(
            bucket_name=S3_BUCKET,
            prefix=prefix,
            recursive=False  # On ne liste que les répertoires de premier niveau
        )
        for obj in objects_iter:
            key = obj.object_name
            if key.startswith(prefix) and key.endswith("/"):
                date_str = key[len(prefix):-1]  # Extrait la partie YYYY-MM-DD
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                    found_dates.add(dt)
                except ValueError:
                    continue
    except S3Error:
        found_dates = set()
    
    if not found_dates:
        return datetime.strptime(INITIAL_DATE, "%Y-%m-%d").date()
    return max(found_dates) + timedelta(days=1)

def process_database(minio_client: Minio, watcher_pid: int = None) -> None:
    """
    Traite la base pour la prochaine situation_date,
    Écrit DIRECTEMENT en S3A (MinIO).
    """
    pid = os.getpid()
    try:
        spark = _init_spark()
        spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
        next_date = _get_next_situation_date_minio(minio_client)
        next_date_str = next_date.strftime("%Y-%m-%d")
        print(f"Processing database for situation_date={next_date_str}")

        # Lecture JDBC depuis Postgres
        jdbc_url = (
            f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_NAME}"
            f"?user={PG_USER}&password={PG_PASSWORD}"
        )
        query = f"(SELECT * FROM {PG_TABLE} WHERE situation_date = '{next_date_str}') AS subq"
        df = (
            spark.read
                 .format("jdbc")
                 .option("url", jdbc_url)
                 .option("dbtable", query)
                 .option("driver", "org.postgresql.Driver")
                 .load()
        )

        if df.rdd.isEmpty():
            print(f"No data found for situation_date={next_date_str}; skipping.")
            return

        df_repart = df.repartition(DB_NUM_PARTITIONS)

        # Cible S3A (MinIO)
        s3a_target = f"s3a://{S3_BUCKET}/{S3_DATALAKE_PREFIX}/{PG_NAME}"

        df_repart.write \
            .mode("overwrite") \
            .option("maxRecordsPerFile", 10_000_000) \
            .partitionBy("situation_date") \
            .parquet(s3a_target)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Database export COMPLETE (direct S3A) for situation_date={next_date_str}")
        os.kill(pid, FEEDER_SIG_DB)
        if watcher_pid:
            try:
                os.kill(watcher_pid, FEEDER_SIG_DB)
            except ProcessLookupError:
                print(f"[WARN] watcher PID {watcher_pid} not found; skipping external signal.", file=sys.stderr)

    except Exception as e:
        print(f"[ERROR][DB JOB]: {e}", file=sys.stderr)


def main():
    watcher_pid = None
    if len(sys.argv) > 1:
        try:
            watcher_pid = int(sys.argv[1])
        except ValueError:
            print("[FATAL] Second argument must be an integer (watcher PID).", file=sys.stderr)
            sys.exit(1)

    try:
        resp = requests.get(urljoin(API_BASE_URL + "/", "files"))
        resp.raise_for_status()
        all_files = sorted(resp.json())
    except Exception as e:
        print(f"[FATAL] Could not list files from API: {e}", file=sys.stderr)
        sys.exit(1)

    file_to_signal = {fname: FILE_SIGNAL_MAP.get(fname, None) for fname in all_files}

    # Enregistrement des handlers de signaux pour chaque fichier
    for fname, sig in file_to_signal.items():
        if sig is None:
            print(f"[WARN] No signal mapping for {fname}; skipping.")
            continue

        def handler_factory(name):
            def _handler(signum, frame):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{ts}] 🔔 Received signal {signum} → '{name}' ingestion finished.")
            return _handler

        signal.signal(sig, handler_factory(fname))

    # Handlers pour DB et DONE
    signal.signal(FEEDER_SIG_DB,  lambda s, f: print(f"[DB] Received FEEDER_SIG_DB ({FEEDER_SIG_DB})"))
    signal.signal(FEEDER_SIG_DONE, lambda s, f: print(f"[DONE] Received FEEDER_SIG_DONE ({FEEDER_SIG_DONE})"))

    minio_client = _init_minio_client()
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    futures = [
        executor.submit(process_single_file, fname, minio_client, file_to_signal[fname], watcher_pid)
        for fname in all_files if fname in FILE_SIGNAL_MAP
    ]
    futures.append(executor.submit(process_database, minio_client, watcher_pid))

    for fut in futures:
        try:
            fut.result()
        except Exception as e:
            print(f"[ERROR] raised exception: {e}", file=sys.stderr)

    executor.shutdown(wait=True)
    print("[MAIN] All ingestion tasks have finished. Sending DONE signal.")
    os.kill(os.getpid(), FEEDER_SIG_DONE)
    if watcher_pid:
        try:
            os.kill(watcher_pid, FEEDER_SIG_DONE)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    main()
