# Utilise l'image officielle Postgres 17 comme base
FROM postgres:17

# 1) Définit l'utilisateur, le mot de passe et la base par défaut pour Hive
ENV POSTGRES_USER=hiveuser
ENV POSTGRES_PASSWORD=hivepassword
ENV POSTGRES_DB=hive_metastore

# 2) Force l'authentification MD5 pour tous les accès dès l'initdb
ENV POSTGRES_INITDB_ARGS="--auth-local=md5 --auth-host=md5"

# 3) Copie le script d'initialisation SQL dans le dossier d'init de Postgres
COPY init.sql /docker-entrypoint-initdb.d/