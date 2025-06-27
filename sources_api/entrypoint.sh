#!/usr/bin/env bash
set -euo pipefail

until pg_isready -h postgres -p 5432 -U myuser; do
  echo >&2 "Postgres n'est pas disponible — en attente"
  sleep 2
done

# 1) Pour chaque CSV dans transactions_fraud_datasets/, charger dans Postgres
#    Vous pouvez passer la base cible via des variables d'environnement si vous le souhaitez, ou coder en dur comme dans db.py.
echo "→ Alimentation de la table depuis transaction_data_part1.csv"
python db.py "transaction_data_part1.csv"

echo "Postgres est prêt — exécution de la commande"
# 2) Exécute la commande finale (uvicorn…) pour que les signaux soient bien propagés
exec "$@"