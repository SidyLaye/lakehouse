FROM python:3.11-slim

# 1) Set up working dir & environment
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# 2) Install OS deps for psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         gcc libpq-dev postgresql-client\
    && rm -rf /var/lib/apt/lists/*

# 3) Install Python requirements (make sure requirements.txt lists sqlalchemy, pandas, psycopg2-binary, uvicorn, fastapi…)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy your code & data
COPY api.py ./
COPY db.py ./
COPY transactions_fraud_datasets/ ./transactions_fraud_datasets/
COPY transaction_data_part1.csv ./transaction_data_part1.csv

# 5) Add entrypoint that seeds the DB then starts Uvicorn
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# 6) Expose port & switch to entrypoint
EXPOSE 9998
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "9998"]
