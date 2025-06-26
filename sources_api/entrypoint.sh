#!/usr/bin/env bash
set -euo pipefail

until pg_isready -h postgres -p 5432 -U myuser; do
  echo >&2 "Postgres is unavailable — sleeping"
  sleep 2
done

# 1) For each CSV in transactions_fraud_datasets/, load into Postgres
#    You may pass the target DB via env vars if you like, or hard-code as in db.py.
echo "→ Seeding table from transaction_data_part1.csv"
python db.py "transaction_data_part1.csv"

echo "Postgres is up — executing command"
# 2) Exec the final command (uvicorn…) so signals propagate properly
exec "$@"