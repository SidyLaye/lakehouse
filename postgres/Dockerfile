FROM postgres:17

# 1) User par défaut pour Hive
ENV POSTGRES_USER=hiveuser
ENV POSTGRES_PASSWORD=hivepassword
ENV POSTGRES_DB=hive_metastore

# 2) Force MD5 pour tous les accès dès l'initdb
ENV POSTGRES_INITDB_ARGS="--auth-local=md5 --auth-host=md5"

# 3) Copie du script d'initialisation
COPY init.sql /docker-entrypoint-initdb.d/