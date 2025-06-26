# Dockerfile.api_ml
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive

# 1) System deps: Python3, pip, curl + Java 8 headless (same as lakehouse)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openjdk-8-jdk-headless \
      python3 python3-pip \
      curl wget && \
    rm -rf /var/lib/apt/lists/*

# point JAVA_HOME so pyspark can find it
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# 2) Python deps: FastAPI, Uvicorn, PySpark, Cloudpickle, etc.
RUN pip3 install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        pyspark \
        cloudpickle \
        mlflow \
        pandas \
        minio

WORKDIR /app

# 3) Copy your app code + wait-script
COPY main.py wait-for-model.sh ./

# 4) Make the wait script executable
RUN chmod +x wait-for-model.sh

# 5) Expose the port your FastAPI app listens on
EXPOSE 9997

# 6) When the container starts, wait for the model then launch Uvicorn
ENTRYPOINT ["./wait-for-model.sh"]
