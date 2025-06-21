import os
import psycopg2
from psycopg2 import pool

PG_HOST     = os.getenv("PG_HOST", "localhost")
PG_PORT     = os.getenv("PG_PORT", "5432")
PG_DB       = os.getenv("PG_NAME", "analytics")
PG_USER     = os.getenv("PG_USER", "grafana_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "grafana_pass")

# On crée un pool de connexions (max 5 connexions simultanées par exemple)
postgres_pool = psycopg2.pool.SimpleConnectionPool(
    1,
    5,
    host=PG_HOST,
    port=PG_PORT,
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD
)

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
