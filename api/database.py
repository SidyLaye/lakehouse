import os
import time
import psycopg2
from psycopg2 import pool

PG_HOST     = os.getenv("PG_HOST", "postgres")
PG_PORT     = os.getenv("PG_PORT", "5432")
PG_DB       = os.getenv("PG_NAME", "analytics")
PG_USER     = os.getenv("PG_USER", "grafana_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "grafana_pass")

MAX_RETRIES = 5
SLEEP_BETWEEN = 10  # secondes

postgres_pool = None
for attempt in range(1, MAX_RETRIES + 1):
    try:
        postgres_pool = pool.SimpleConnectionPool(
            1,
            5,
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        print(f"[database] Connected to Postgres on attempt {attempt}")
        break
    except psycopg2.OperationalError as e:
        print(f"[database] Postgres not ready (attempt {attempt}/{MAX_RETRIES}): {e}")
        if attempt == MAX_RETRIES:
            print("[database] All retries failed, cannot connect to Postgres")
            raise
        time.sleep(SLEEP_BETWEEN)

def get_connection():
    """
    Récupère une connexion depuis le pool.
    À utiliser en début de requête.
    """
    return postgres_pool.getconn()

def release_connection(conn):
    """
    Remet la connexion dans le pool.
    À utiliser en fin de requête.
    """
    postgres_pool.putconn(conn)
