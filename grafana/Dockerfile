# 1) Base Ubuntu “propre”
FROM ubuntu:20.04

# 2) Prérequis + sqlite3 pour patcher la DB
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gnupg2 curl ca-certificates sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 3) Ajout du repo officiel Grafana
RUN curl https://packages.grafana.com/gpg.key | apt-key add - && \
    echo "deb https://packages.grafana.com/oss/deb stable main" \
      > /etc/apt/sources.list.d/grafana.list

# 4) Installation de Grafana OSS
RUN apt-get update && \
    apt-get install -y --no-install-recommends grafana && \
    rm -rf /var/lib/apt/lists/*

# 5) Votre config & (vide) provisioning
COPY etc/grafana.ini             /etc/grafana/grafana.ini
COPY provisioning/                /etc/grafana/provisioning/

# 6) Copie de votre DB et data
ENV GF_PATHS_DATA=/var/lib/grafana
COPY data/                        /var/lib/grafana/

# 7) Patch des URLs dans grafana.db
RUN sqlite3 /var/lib/grafana/grafana.db \
      "UPDATE data_source \
          SET url = replace(url, 'http://localhost:9090', 'http://prometheus:9090') \
        WHERE url LIKE 'http://localhost:9090%';" && \
    sqlite3 /var/lib/grafana/grafana.db \
      "UPDATE data_source \
          SET url = replace(url, 'localhost:5432', 'postgres:5432') \
        WHERE url LIKE '%localhost:5432%';"

# 8) Plugins hors du volume par défaut
ENV GF_PLUGIN_DIRS=/var/lib/grafana/plugins
COPY data/plugins/                     /var/lib/grafana/plugins

# 9) Permissions (uid/gid 472 sur Debian)
RUN chown -R 472:472 \
      /etc/grafana \
      /var/lib/grafana \
      /etc/grafana/provisioning \
      /var/lib/grafana/plugins

# 10) Exposer et lancer Grafana
EXPOSE 3000
USER 472
CMD ["/usr/sbin/grafana-server", \
     "--homepath=/usr/share/grafana", \
     "--config=/etc/grafana/grafana.ini"]
