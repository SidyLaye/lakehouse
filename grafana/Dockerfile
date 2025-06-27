# 1) Utilise une image Ubuntu 20.04 propre comme base
FROM ubuntu:20.04

# 2) Installe les prérequis système et sqlite3 pour manipuler la base de données Grafana
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gnupg2 curl ca-certificates sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 3) Ajoute le dépôt officiel Grafana et sa clé GPG
RUN curl https://packages.grafana.com/gpg.key | apt-key add - && \
    echo "deb https://packages.grafana.com/oss/deb stable main" \
      > /etc/apt/sources.list.d/grafana.list

# 4) Installe Grafana OSS
RUN apt-get update && \
    apt-get install -y --no-install-recommends grafana && \
    rm -rf /var/lib/apt/lists/*

# 5) Copie la configuration personnalisée et le provisioning (datasources, dashboards, etc.)
COPY etc/grafana.ini             /etc/grafana/grafana.ini
COPY provisioning/                /etc/grafana/provisioning/

# 6) Copie la base de données et les données (dashboards, etc.)
ENV GF_PATHS_DATA=/var/lib/grafana
COPY data/                        /var/lib/grafana/

# 7) Patch les URLs dans la base grafana.db pour pointer vers les bons services
RUN sqlite3 /var/lib/grafana/grafana.db \
      "UPDATE data_source \
          SET url = replace(url, 'http://localhost:9090', 'http://prometheus:9090') \
        WHERE url LIKE 'http://localhost:9090%';" && \
    sqlite3 /var/lib/grafana/grafana.db \
      "UPDATE data_source \
          SET url = replace(url, 'localhost:5432', 'postgres:5432') \
        WHERE url LIKE '%localhost:5432%';"

# 8) Plugins Grafana hors du volume par défaut
ENV GF_PLUGIN_DIRS=/var/lib/grafana/plugins
COPY data/plugins/                     /var/lib/grafana/plugins

# 9) Met à jour les permissions pour l'utilisateur Grafana (uid/gid 472)
RUN chown -R 472:472 \
      /etc/grafana \
      /var/lib/grafana \
      /etc/grafana/provisioning \
      /var/lib/grafana/plugins

# 10) Expose le port 3000 et lance Grafana sous l'utilisateur 472
EXPOSE 3000
USER 472
CMD ["/usr/sbin/grafana-server", \
     "--homepath=/usr/share/grafana", \
     "--config=/etc/grafana/grafana.ini"]
