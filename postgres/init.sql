-- postgres/init.sql

-- 1) Crée les trois bases de données si elles n'existent pas déjà
SELECT 'CREATE DATABASE hive_metastore'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hive_metastore')\gexec

SELECT 'CREATE DATABASE analytics'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytics')\gexec

SELECT 'CREATE DATABASE mydb'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mydb')\gexec

-- 2) Crée les trois rôles utilisateurs si besoin (ignore l'erreur si déjà existant)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hiveuser') THEN
    CREATE USER hiveuser WITH ENCRYPTED PASSWORD 'hivepassword';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_user') THEN
    CREATE USER grafana_user WITH ENCRYPTED PASSWORD 'grafana_pass';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'myuser') THEN
    CREATE USER myuser WITH ENCRYPTED PASSWORD 'mysupersecret';
  END IF;
END
$$;

-- 3) Donne le droit de connexion à chaque base pour les rôles concernés
GRANT CONNECT ON DATABASE hive_metastore TO hiveuser;
GRANT CONNECT ON DATABASE analytics       TO grafana_user;
GRANT CONNECT ON DATABASE analytics       TO myuser;
GRANT CONNECT ON DATABASE mydb            TO myuser;

-- 4) Dans chaque base, ajuste le schéma PUBLIC pour donner les droits de création/usage
\connect hive_metastore

GRANT USAGE  ON SCHEMA public TO hiveuser;
GRANT CREATE ON SCHEMA public TO hiveuser;
ALTER SCHEMA public OWNER TO hiveuser;

\connect analytics

GRANT USAGE  ON SCHEMA public TO grafana_user;
GRANT CREATE ON SCHEMA public TO grafana_user;
ALTER SCHEMA public OWNER TO grafana_user;

GRANT USAGE  ON SCHEMA public TO myuser;
GRANT CREATE ON SCHEMA public TO myuser;
-- note: public reste possédé par grafana_user, mais myuser peut aussi créer

\connect mydb

GRANT USAGE  ON SCHEMA public TO myuser;
GRANT CREATE ON SCHEMA public TO myuser;
ALTER SCHEMA public OWNER TO myuser;

-- 5) Toujours dans analytics : crée la table events si absente, puis donne les droits
\connect analytics

CREATE TABLE IF NOT EXISTS events (
  id         SERIAL PRIMARY KEY,
  name       TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE events
  TO grafana_user, myuser;
