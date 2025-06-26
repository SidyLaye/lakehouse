FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive

# 1) Dépendances système + création d’un user 'hdfs'
RUN apt-get update && \
    apt-get install -y \
      openjdk-8-jdk-headless \
      python3 python3-pip \
      git ssh rsync wget curl tar lsof mc nano postgresql-client && \
    useradd --create-home --shell /bin/bash hdfs && \
    mkdir -p /home/hdfs/.ssh && \
    rm -rf /var/lib/apt/lists/*

# 2) Java
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# 3) Spark client + Hadoop
COPY hadoop-3.3.6 /opt/hadoop-3.3.6
COPY spark-3.5.6  /opt/spark-3.5.6
RUN ln -s /opt/hadoop-3.3.6 /opt/hadoop \
 && ln -s /opt/spark-3.5.6  /opt/spark

ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV SPARK_HOME=/opt/spark
ENV PATH="$SPARK_HOME/bin:$PATH"
ENV PATH="$HADOOP_HOME/bin:$PATH"
ENV YARN_CONF_DIR=$HADOOP_CONF_DIR
ENV SMTP_HOST="smtp.gmail.com"
ENV SMTP_PORT="587"
ENV SMTP_USER="sarrsidylaye@gmail.com"
ENV ALERT_EMAIL="sarrsidylaye@gmail.com"
ENV ES_HOST="https://elasticsearch:9200"
ENV ES_INDEX="pipeline-logs"
ENV ES_BULK_SIZE="100"
ENV ES_FLUSH_INTERVAL="5"
ENV PROM_PORT="8000"

ENV SMTP_PASS='hjrsaafooovinydz'

# 4) Hive
COPY apache-hive-3.1.3-bin /opt/hive-3.1.3
RUN ln -s /opt/hive-3.1.3 /opt/hive \
 && chown -R hdfs:hdfs /opt/hadoop-3.3.6 /opt/spark-3.5.6 /opt/hive-3.1.3

ENV HIVE_HOME=/opt/hive
ENV PATH="$HIVE_HOME/bin:$PATH"
ENV HIVE_CONF_DIR=$HIVE_HOME/conf
ENV HIVE_AUX_JARS_PATH="$HADOOP_HOME/share/hadoop/common/lib/*:$HADOOP_HOME/share/hadoop/tools/lib/*"

# 5) Configure Hadoop/YARN daemons to run as 'hdfs'
ENV HDFS_NAMENODE_USER=hdfs \
    HDFS_DATANODE_USER=hdfs \
    HDFS_SECONDARYNAMENODE_USER=hdfs \
    YARN_RESOURCEMANAGER_USER=hdfs \
    YARN_NODEMANAGER_USER=hdfs

RUN wget -q https://dl.min.io/server/minio/release/linux-amd64/minio \
     -O /usr/local/bin/minio && \
    chmod +x /usr/local/bin/minio && \
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc \
     -O /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# 6) Précréer les répertoires HDFS temporaires et donner les droits
RUN mkdir -p /tmp/hadoop-ghost/dfs/name \
         /tmp/hadoop-ghost/dfs/data && \
    chown -R hdfs:hdfs /tmp/hadoop-ghost

# 7) Python deps (as root)
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copier le plugin MLflow
COPY mlflow_minio_artifact_repo.py /app/pipeline/mlflow_minio_artifact_repo.py 

# 8) Copier votre code
COPY orchestrator.py      ./
COPY pipeline/            ./pipeline/
ADD https://jdbc.postgresql.org/download/postgresql-42.7.5.jar /app/pipeline/postgresql-42.7.5.jar

# 9) Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
 && chown -R hdfs:hdfs /app /entrypoint.sh

EXPOSE 9870 9864 8088 7077 8080 10000 10002 8000 9000 9001 5000 1000
ENTRYPOINT ["/entrypoint.sh"]

