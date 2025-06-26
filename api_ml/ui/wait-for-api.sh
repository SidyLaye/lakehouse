#!/usr/bin/env bash
set -e

API_URL="http://api_ml:9997/"

echo "→ Waiting for API at ${API_URL}"
until curl -sf "$API_URL"
do
  sleep 3
done

echo "→ API is up — starting Streamlit UI"
exec streamlit run streamlit_app.py \
     --server.port=8501 \
     --server.address=0.0.0.0
