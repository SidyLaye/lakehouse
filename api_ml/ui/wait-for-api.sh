#!/usr/bin/env bash
set -e

# URL de l'API à attendre
API_URL="http://api_ml:9997/"

echo "→ Waiting for API at ${API_URL}"
# Boucle jusqu'à ce que l'API soit disponible
until curl -sf "$API_URL"
do
  sleep 3
done

echo "→ API is up — starting Streamlit UI"
# Lancement de l'application Streamlit
exec streamlit run streamlit_app.py \
     --server.port=8501 \
     --server.address=0.0.0.0
