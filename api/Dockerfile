FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Variables d'environnement pour connexions
ENV PG_HOST=${PG_HOST:-postgres}
ENV PG_PORT=${PG_PORT:-5432}
ENV PG_USER=${PG_USER:-myuser}
ENV PG_PASSWORD=${PG_PASSWORD:-mysupersecret}
ENV PG_DB=${PG_DB:-analytics}
ENV MINIO_ENDPOINT=${MINIO_ENDPOINT:-http://minio:9000}
ENV MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
ENV MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
ENV ES_HOST=${ES_HOST:-http://elasticsearch:9200}

# Installer dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'API Datamarts
COPY . ./

# Exposer port
EXPOSE 9999

# Lancer l'application FastAPI via le module fastapi_app
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "9999"]