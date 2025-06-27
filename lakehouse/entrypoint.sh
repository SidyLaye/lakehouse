#!/usr/bin/env bash
set -e

# 0) Démarrer SSHD (nécessaire pour Hadoop)
service ssh start

# 1) Générer une paire de clés SSH pour hdfs si elle n'existe pas encore
if [ ! -f /home/hdfs/.ssh/id_rsa ]; then
  echo "→ Génération de la paire de clés SSH pour hdfs"
  mkdir -p /home/hdfs/.ssh
  chown hdfs:hdfs /home/hdfs/.ssh
  chmod 700 /home/hdfs/.ssh

  # Générer la clé sous hdfs
  su - hdfs -c "ssh-keygen -t rsa -b 2048 \
    -f /home/hdfs/.ssh/id_rsa -q -N '' -C 'hdfs@localhost'"

  # Autoriser la clé publique
  cat /home/hdfs/.ssh/id_rsa.pub >> /home/hdfs/.ssh/authorized_keys
  chown hdfs:hdfs /home/hdfs/.ssh/authorized_keys
  chmod 600 /home/hdfs/.ssh/authorized_keys
fi

# 2) Pré‐ajouter localhost dans known_hosts pour éviter l’invite interactive
# (utile pour les accès SSH locaux)
echo "→ Ajout de localhost dans known_hosts"
mkdir -p /home/hdfs/.ssh
ssh-keyscan -H localhost >> /home/hdfs/.ssh/known_hosts
chown hdfs:hdfs /home/hdfs/.ssh/known_hosts
chmod 644 /home/hdfs/.ssh/known_hosts

# 3) Démarrer MinIO et créer le bucket lakehouse
minio server /data --console-address ":9001" &
echo "→ MinIO démarré sur ports 9000 (API) et 9001 (Console)"
sleep 2

# Configuration du client MinIO (mc) et création du bucket
mc alias set local http://localhost:9000 \
    "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minioadmin}" --api S3v4
echo "→ Alias MC configuré"
mc alias list
mc mb --ignore-existing local/lakehouse
echo "→ Bucket 'lakehouse' OK"

# 4) Format HDFS et démarrage des services HDFS/YARN
if [ ! -f /tmp/hdfs_init ]; then
  echo "→ Format du NameNode HDFS"
  $HADOOP_HOME/bin/hdfs namenode -format -force
  touch /tmp/hdfs_init
fi

echo "→ Démarrage Hadoop"
$HADOOP_HOME/sbin/start-all.sh

# 3) Attendre Postgres (vérifie que la base est prête avant de continuer)
echo -n "→ Waiting for PostgreSQL…"
until psql "postgresql://hiveuser:hivepassword@postgres:5432/hive_metastore?sslmode=disable" -c '\q' 2>/dev/null; do
  echo -n "."
  sleep 2
done
echo " OK"

# 4) Vérifier si la table VERSION existe et choisir init ou upgrade
EXISTS=$(psql \
  "postgresql://hiveuser:hivepassword@postgres:5432/hive_metastore?sslmode=disable" \
  -tAc "SELECT 1
         FROM information_schema.tables
        WHERE table_schema='public' AND table_name='version'
        LIMIT 1;")

if [ "$EXISTS" = "1" ]; then
  echo "→ VERSION exists; running upgradeSchema"
  bash -lc '
    export PATH=/opt/hadoop/bin:$PATH
    export HADOOP_HOME=/opt/hadoop
    export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
    export YARN_CONF_DIR=/opt/hadoop/etc/hadoop
    /opt/hive/bin/schematool -dbType postgres -upgradeSchema
  '
else
  echo "→ VERSION missing; running initSchema"
  bash -lc '
    export PATH=/opt/hadoop/bin:$PATH
    export HADOOP_HOME=/opt/hadoop
    export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
    export YARN_CONF_DIR=/opt/hadoop/etc/hadoop
    /opt/hive/bin/schematool -dbType postgres -initSchema
  '
fi

# 5) Démarrer le metastore Hive
bash -lc '
  export PATH=/opt/hadoop/bin:$PATH
  export HADOOP_HOME=/opt/hadoop
  export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
  export YARN_CONF_DIR=/opt/hadoop/etc/hadoop
  /opt/hive/bin/hive --service metastore &
'

# ——— Wait for sources_api to be healthy ———
echo -n "→ Waiting for sources_api at http://sources_api:9998/files "
until curl -sf http://sources_api:9998/files >/dev/null; do
  echo -n "."; sleep 2
done
echo " OK"

# ———  Start MLflow UI ———
echo "→ Starting MLflow UI on :5000"
mlflow ui \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root minio://lakehouse/mlflow-artifacts \
  &
  
# Démarre un serveur HTTP pour exposer les artefacts du pipeline
python3 -m http.server 1000 \
    --bind 0.0.0.0 \
    --directory /app/pipeline &

# 6) Lancer l’orchestrateur (pipeline principal)
bash -lc '
  export PATH=/opt/hadoop/bin:$PATH
  export HADOOP_HOME=/opt/hadoop
  export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
  export YARN_CONF_DIR=/opt/hadoop/etc/hadoop
  cd /app && python3 -u orchestrator.py 
'

# 3) Quand orchestrator se termine, on garde le container UP pour MLflow
echo "→ Orchestrator exited, MLflow UI is still running at http://localhost:5000"
# On bloque ici sans consommer de CPU
tail -f /dev/null