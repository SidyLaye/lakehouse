-- postgres/init.sql

-- 1) Conditionally create the three databases
SELECT 'CREATE DATABASE hive_metastore'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hive_metastore')\gexec

SELECT 'CREATE DATABASE analytics'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytics')\gexec

SELECT 'CREATE DATABASE mydb'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mydb')\gexec

-- 2) Create the three roles (they’ll error if already there, but that’s ok)
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

-- 3) Grant CONNECT on each DB
GRANT CONNECT ON DATABASE hive_metastore TO hiveuser;
GRANT CONNECT ON DATABASE analytics       TO grafana_user;
GRANT CONNECT ON DATABASE analytics       TO myuser;
GRANT CONNECT ON DATABASE mydb            TO myuser;

-- 4) In each DB, adjust the PUBLIC schema so the correct role can CREATE/USE
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
-- note: public remains owned by grafana_user, but myuser can also create

\connect mydb

GRANT USAGE  ON SCHEMA public TO myuser;
GRANT CREATE ON SCHEMA public TO myuser;
ALTER SCHEMA public OWNER TO myuser;

-- 5) Still in analytics: create your events table if missing, then grant access
\connect analytics

CREATE TABLE IF NOT EXISTS events (
  id         SERIAL PRIMARY KEY,
  name       TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE events
  TO grafana_user, myuser;
