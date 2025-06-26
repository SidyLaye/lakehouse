#!/usr/bin/env bash
set -e

MODEL_URL="http://lakehouse:1000/fraud_model_mlflow/"
MODEL_DIR="/app/pipeline/fraud_model_mlflow"

echo "→ Waiting for $MODEL_URL to be available …"
until curl --silent --head --fail "$MODEL_URL" >/dev/null; do
  echo -n "."
  sleep 5
done
echo
echo "→ $MODEL_URL is up, downloading the model tree…"

wget -r -np -nH -R "index.html*" -P /app/pipeline "$MODEL_URL"

echo "→ Model directory content:"
ls -R "$MODEL_DIR"

# -- ensuite, même logique pour le pickle --
PKL_URL="http://lakehouse:1000/fraud_logreg.pkl"
PKL_DST="/app/fraud_logreg.pkl"

echo "→ Waiting for $PKL_URL to be available …"
until curl --silent --head --fail "$PKL_URL" >/dev/null; do
  echo -n "."
  sleep 5
done
echo
echo "→ Downloading pickle…"
curl --fail --location "$PKL_URL" -o "$PKL_DST"

echo "→ Starting API…"
exec uvicorn main:app --host 0.0.0.0 --port 9997
