# Utilise l'image officielle Elasticsearch version 7.17.0
FROM docker.elastic.co/elasticsearch/elasticsearch:7.17.0

# Configure Elasticsearch pour fonctionner en mode single-node (pas de cluster)
ENV discovery.type=single-node

# Désactive la sécurité X-Pack (pas d'authentification ni SSL pour un usage local/dev)
ENV xpack.security.enabled=false