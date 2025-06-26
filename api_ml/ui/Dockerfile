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

# 1) Install runtime deps
RUN pip install --no-cache-dir \
        streamlit \
        requests \
        pandas \
        plotly \
        pyspark

WORKDIR /app

# 2) Copy your code + wait-script
COPY streamlit_app.py wait-for-api.sh ./

RUN chmod +x wait-for-api.sh

# 3) Expose port and run waiter
EXPOSE 8501
ENTRYPOINT ["./wait-for-api.sh"]
