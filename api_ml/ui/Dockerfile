# Dockerfile.api_ml
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive

# 1) Dépendances système : Python3, pip, curl, Java 8 headless (pour PySpark)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openjdk-8-jdk-headless \
      python3 python3-pip \
      curl wget && \
    rm -rf /var/lib/apt/lists/*

# Définir JAVA_HOME pour PySpark
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# 1) Installation des dépendances Python nécessaires à l'UI
RUN pip install --no-cache-dir \
        streamlit \
        requests \
        pandas \
        plotly \
        pyspark

WORKDIR /app

# 2) Copier le code de l'UI et le script d'attente
COPY streamlit_app.py wait-for-api.sh ./

RUN chmod +x wait-for-api.sh

# 3) Exposer le port Streamlit et lancer le script d'attente
EXPOSE 8501
ENTRYPOINT ["./wait-for-api.sh"]
