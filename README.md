# 🏗️ Lakehouse — Plateforme complète de détection de fraude, orchestration, analyse et déploiement cloud

Ce projet propose une architecture data/ML moderne, modulaire et automatisée, pour la détection de fraude, l’analyse de données, le monitoring, la visualisation et le déploiement cloud. Chaque composant, script et configuration est abondamment commenté pour faciliter la compréhension, la maintenance et l’extension du projet.

---

## 🚀 Fonctionnalités principales
- **API FastAPI** (`api/`) : endpoints REST pour la détection de fraude, documentation Swagger, code commenté (routes, schémas, accès BDD, features).
- **API sources** (`sources_api/`) : ingestion, split, alimentation PostgreSQL, scripts Python commentés (api.py, db.py, split.py, entrypoint.sh, requirements.txt).
- **Pipeline Lakehouse** (`lakehouse/`) : orchestration Spark, MLflow, MinIO, scripts pipeline (datamarts, feeder, ml, preprocessing, signals), tous commentés section par section.
- **Machine Learning API** (`api_ml/api/`) : API FastAPI dédiée à l’inférence ML, Dockerfile et scripts commentés.
- **Interface utilisateur ML** (`api_ml/ui/`) : application Streamlit pour la prédiction et la visualisation, code et Dockerfile commentés.
- **Base de données PostgreSQL** (`postgres/`) : Dockerfile et script d’initialisation SQL commentés.
- **Elasticsearch** (`elasticsearch/`) : Dockerfile commenté.
- **Monitoring Prometheus** (`prometheus/`) : Dockerfile et prometheus.yml commentés (explication de chaque cible et métrique).
- **Visualisation Grafana** (`grafana/`) : Dockerfile commenté, provisioning automatisé.
- **Déploiement automatisé** (`srv/`) : scripts Bash, Terraform, Ansible, génération dynamique d’inventaire, tous abondamment commentés.

---

## 📦 Démarrage rapide (local, Docker Compose)

### Prérequis
- Docker et Docker Compose installés
- Ports suivants disponibles : 5432, 9999, 9998, 1000, 5000, 9870, 8088, 7077, 8000, 9000, 9001, 9200, 9090, 3000, 9997, 8501

### Lancement des services
```bash
docker compose build
# puis
docker compose up -d
```

### Arrêt et gestion des services
```bash
docker compose down           # Arrêt de tous les services
docker compose logs -f        # Logs en temps réel
docker compose ps             # Statut des conteneurs
docker compose build --no-cache  # Reconstruction complète
```

### Accès aux interfaces
- **API principale** : http://localhost:9999/docs (Swagger)
- **API sources** : http://localhost:9998/docs
- **Interface ML (Streamlit)** : http://localhost:8501
- **Grafana** : http://localhost:3000
- **Prometheus** : http://localhost:9090

---

## 🗺️ Architecture détaillée du projet

```
.
├── docker-compose.yml         # Orchestration multi-conteneurs, chaque service/port/dépendance commenté
├── api/                      # Backend FastAPI (routes, schémas, BDD, features, tout commenté)
│   ├── fastapi_app.py        # Application principale FastAPI, routes, logique métier
│   ├── database.py           # Connexion PostgreSQL, gestion sessions
│   ├── schemas.py            # Modèles Pydantic, validation
│   ├── routers/              # Routes modulaires (features, risques, etc.), chaque fichier commenté
│   └── ...
├── sources_api/              # API d’ingestion, split, alimentation BDD
│   ├── api.py                # FastAPI pour ingestion, routes commentées
│   ├── db.py                 # Chargement CSV → PostgreSQL, logique commentée
│   ├── split.py              # Découpe de CSV, script commenté ligne à ligne
│   ├── entrypoint.sh         # Script d’entrée, attente BDD, alimentation, commentaires FR
│   ├── requirements.txt      # Dépendances, chaque ligne expliquée
│   └── ...
├── lakehouse/                # Orchestration, pipeline, MLflow, Spark, MinIO
│   ├── orchestrator.py       # Orchestration globale, gestion des jobs, commentaires détaillés
│   ├── mlflow_minio_artifact_repo.py # Intégration MLflow/MinIO, explications
│   ├── entrypoint.sh         # Script d’entrée, commentaires sur chaque étape
│   ├── pipeline/             # Scripts pipeline (datamarts, feeder, ml, preprocessing, signals), chaque script commenté
│   └── ...
├── api_ml/                   # API ML et UI Streamlit
│   ├── api/main.py           # API FastAPI ML, endpoints, logique, commentaires
│   ├── api/Dockerfile        # Dockerfile commenté
│   ├── ui/streamlit_app.py   # Interface Streamlit, logique, UI, commentaires
│   ├── ui/Dockerfile         # Dockerfile commenté
│   └── ...
├── postgres/                 # Base de données PostgreSQL
│   ├── Dockerfile            # Dockerfile commenté
│   ├── init.sql              # Script d’initialisation SQL, chaque commande expliquée
├── elasticsearch/            # Dockerfile commenté
├── prometheus/               # Dockerfile, prometheus.yml commentés (explication de chaque section)
├── grafana/                  # Dockerfile commenté
├── srv/                      # Déploiement cloud (scripts, Ansible, Terraform)
│   ├── deploy_pipeline.sh    # Script Bash, chaque étape expliquée
│   ├── ansible/              # Playbook, inventaire, templates, scripts Python, tous commentés
│   ├── infra/                # main.tf, variables.tf, chaque ressource/variable expliquée
│   └── ...
├── .lfsconfig                # Config LFS, commentaire sur l’usage
└── README.md                 # Ce fichier, guide complet
```

---

## 📦 Images Docker pré-compilées

Toutes les images Docker nécessaires au projet sont déjà compilées et disponibles dans le registre GitLab :

➡️ https://gitlab.com/SidyLaye/lakehouse-lfs/container_registry/

Vous pouvez les utiliser directement dans vos déploiements (cloud, CI/CD, etc.) sans avoir à reconstruire les images localement.

---

## 📝 Détail des fichiers commentés et pédagogiques

- **docker-compose.yml** : chaque service, port, dépendance et réseau expliqué.
- **api/** : routes, schémas, accès BDD, routers, tout commenté pour la compréhension métier et technique.
- **sources_api/** :
  - `api.py`, `db.py`, `split.py`, `entrypoint.sh` : chaque fonction, section, logique métier expliquée en français.
  - `requirements.txt` : chaque dépendance explicitée.
- **lakehouse/** :
  - `orchestrator.py`, `mlflow_minio_artifact_repo.py`, `entrypoint.sh` : orchestration, gestion artefacts, scripts d’entrée, tous commentés.
  - `pipeline/` : chaque script (datamarts, feeder, ml, preprocessing, signals) commenté pour expliquer la logique métier et technique.
- **api_ml/** :
  - `api/main.py`, `ui/streamlit_app.py` : endpoints, logique ML, UI, tout commenté.
  - Dockerfile de chaque sous-module commenté.
- **postgres/** : Dockerfile et init.sql commentés (explication de chaque commande SQL).
- **elasticsearch/**, **prometheus/**, **grafana/** : Dockerfile et fichiers de configuration commentés.
- **srv/** :
  - `deploy_pipeline.sh` : script Bash, chaque étape expliquée (variables, Terraform, Ansible, etc.).
  - `ansible/` : playbook, inventaire, templates Jinja2, scripts Python, tous commentés pour le déploiement automatisé.
  - `infra/` : `main.tf`, `variables.tf` (Terraform), chaque ressource et variable expliquée.
- **.lfsconfig** : configuration LFS, commentaire sur l’usage.

---

## ⚙️ Déploiement cloud (AWS EC2, Terraform, Ansible)

### Étapes détaillées
1. **Préparer les credentials** :
   - Modifier les fichiers sous `srv/_credentials` (clé AWS, clé SSH, etc.).
2. **Adapter les variables** :
   - Modifier les variables dans `srv/deploy_pipeline.sh` et `srv/infra/variables.tf` selon votre environnement (profil AWS, région, type d’instance, etc.).
3. **Lancer le déploiement** :
   ```sh
   cd srv
   bash deploy_pipeline.sh
   ```
   - Provisionnement de l’infrastructure (tofu/Terraform)
   - Génération dynamique de l’inventaire Ansible (template Jinja2, script Python commenté)
   - Déploiement automatisé de tous les services Docker sur les VMs (playbook Ansible commenté)

Chaque étape, script et configuration est abondamment commenté pour vous guider.

---

## 🔬 Exemples d’utilisation

### Appel API de prédiction (FastAPI ML)

L’API de prédiction est exposée par le service `api_ml` sur le port 9997 (voir docker-compose.yml). Pour y accéder depuis un autre conteneur ou via le réseau Docker, utilisez l’URL suivante :

```
http://api_ml:9997/predict
```

Pour tester depuis l’hôte (si le port 9997 est exposé), utilisez :

```
http://localhost:9997/predict
```

#### Exemple de requête curl (depuis l’hôte)
```sh
curl -X POST "http://localhost:9997/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "amount": 123.45,
       "card_brand": "VISA",
       "card_type": "CREDIT",
       "merchant_state": "NY",
       "use_chip": "True",
       "credit_limit": 5000,
       "per_capita_income": 35000,
       "yearly_income": 42000,
       "total_debt": 1000,
       "credit_score": 700,
       "num_credit_cards": 2
     }'
```

Réponse attendue :
```json
{
  "fraud_probability": 0.15,
  "is_fraud": false,
  "confidence": "Moyenne"
}
```

> **Remarque** : L’URL de l’API peut différer selon votre environnement (réseau Docker, cloud, etc.). Dans l’interface Streamlit, l’URL par défaut est `http://api_ml:9997` (modifiable dans la barre latérale).

### Utilisation de l’interface Streamlit
- Accédez à l’URL du service `ui_api_ml` (par défaut http://localhost:8501 si exposé).
- Renseignez l’URL de l’API ML dans la barre latérale si besoin.
- Remplissez le formulaire, cliquez sur "Prédire" pour obtenir le résultat, visualisez les métriques et l’historique.

### Gestion des conteneurs
```sh
docker compose logs -f         # Logs en temps réel
docker compose exec api bash   # Accès shell au conteneur API
docker compose exec ui_api_ml bash # Accès shell à l’UI ML
```

---

## 👥 Contributeurs

Merci à tous les contributeurs du projet :
- [SidyLaye](https://github.com/SidyLaye)
- [adamowski13](https://github.com/adamowski13)
- [Lolowyn](https://github.com/Lolowyn)

Contributions, issues et suggestions sont les bienvenues !

---

## 📚 Ressources utiles
- Documentation FastAPI : https://fastapi.tiangolo.com/
- Documentation Streamlit : https://docs.streamlit.io/
- Documentation Docker Compose : https://docs.docker.com/compose/
- Documentation Terraform : https://www.terraform.io/docs/
- Documentation Ansible : https://docs.ansible.com/

---

## 📝 Licence
Ce projet est distribué sous licence MIT.
