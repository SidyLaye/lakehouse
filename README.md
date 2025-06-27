<<<<<<< HEAD
<!-- ⚠️ This README has been generated from the file(s) "blueprint.md" ⚠️-->
[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#lakehouse)
=======
# lakehouse
Pour run le projet sur AWS (Instances Ec2) :

-Pull srv/

-Mordifier les fichier sous srv/_credentials

-modifier les variables dans srv/deploy_pipeline.sh et srv/infra/variables.tf

-Run le script shell

# lakehouse
# Fraud Detection API
>>>>>>> cb5b0ec07bd2b86755c768f132cd95d74bc651aa

# ➤ lakehouse

[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#lakehouse)

# ➤ lakehouse

[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#fraud-detection-api)

# ➤ Fraud Detection API


[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#-dploiement-avec-docker-compose)

## ➤ 🔧 Déploiement avec Docker Compose

### Prérequis

- Docker et Docker Compose installés
- Ports 5432, 9999, 9998, 1000, 5000, 9870, 8088, 7077, 8000, 9000, 9001, 9200, 9090, 3000, 9997, 8501 disponibles

### Lancement rapide

```bash
docker compose build
# puis
docker compose up -d
```

### Services disponibles

| Service | URL | Description |
|---------|-----|-------------|
| API Fraud Detection | http://localhost:8000 | API REST de prédiction |
| Documentation API | http://localhost:8000/docs | Interface Swagger automatique |
| Interface Streamlit | http://localhost:8501 | Interface web interactive |

### Test de l'API

#### Accès à l'interface Swagger

```
http://localhost:8000/docs
```

#### Test avec fichier JSON

```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d @test_fraud.json
```

#### Exemple de requête de prédiction

```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "feature1": 1.2,
       "feature2": 0.8,
       "feature3": 2.1
     }'
```


[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#-interface-streamlit)

## ➤ 🎯 Interface Streamlit

### Accès à l'interface web

L'application Streamlit est disponible à l'adresse :

```
http://localhost:8501
```

### Fonctionnalités

- **Interface intuitive** : Formulaire web pour saisir les données
- **Prédiction temps réel** : Résultats instantanés
- **Visualisations** : Graphiques et métriques interactives
- **Historique** : Consultation des prédictions précédentes

### Utilisation

1. Naviguez vers http://localhost:8501
2. Remplissez les champs du formulaire avec les données de transaction
3. Cliquez sur "Prédire" pour obtenir le résultat
4. Consultez la probabilité de fraude et la classification

### Gestion des containers

#### Arrêt des services

```bash
docker compose down
```

#### Consultation des logs

```bash
docker compose logs -f
```

#### Reconstruction après modification

```bash
docker compose build --no-cache
docker compose up -d
```


[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#-utilisation-de-lapi)

## ➤ 📊 Utilisation de l'API

### Endpoints disponibles

- `POST /predict` - Prédiction de fraude
- `GET /docs` - Documentation Swagger
- `GET /redoc` - Documentation alternative

### Format des données

L'API attend un JSON avec les features du modèle de détection de fraude. Consultez le fichier `test_fraud.json` pour un exemple complet.

### Réponse de l'API

```json
{
  "prediction": 0,
  "probability": 0.15,
  "status": "success"
}
```


[![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/colored.png)](#-dveloppement)

## ➤ 🛠️ Développement

### Structure du projet

```
.
├── docker-compose.yml
├── api/                # Backend FastAPI (fraude)
├── sources_api/        # API d'ingestion
├── lakehouse/          # Orchestration, pipeline, MLflow, Spark, MinIO
├── api_ml/             # API ML et UI Streamlit
├── postgres/           # Base de données
├── elasticsearch/      # Moteur de recherche
├── prometheus/         # Monitoring
├── grafana/            # Visualisation
├── srv/                # Déploiement (Terraform, Ansible)
└── ...
```

### Logs et debugging

Pour suivre les logs en temps réel :

```bash
docker compose logs -f
```

### Accès aux containers

```bash
# ➤ Accès au container API
docker-compose exec fraud-api bash


# ➤ Accès au container Streamlit
docker-compose exec streamlit-app bash
```

---

## 🏗️ Lakehouse — Plateforme de détection de fraude, orchestration et analyse de données

Ce projet propose une architecture complète de type "lakehouse" pour la détection de fraude, l'analyse de données, le monitoring, la visualisation et le déploiement automatisé. Il s'appuie sur Docker Compose pour l'orchestration locale, et sur Terraform/Ansible pour le déploiement cloud.

---

## 🚀 Fonctionnalités principales
- **API FastAPI** (`api/`) : expose des endpoints REST pour la détection de fraude en temps réel, documentation Swagger intégrée.
- **API sources** (`sources_api/`) : ingestion, split et gestion des données sources, alimentation de la base PostgreSQL.
- **Pipeline Lakehouse** (`lakehouse/`) : orchestration Spark, MLflow, MinIO, scripts de pipeline, gestion des signaux, datamarts, preprocessing, etc.
- **Machine Learning API** (`api_ml/api/`) : API FastAPI dédiée à l'inférence ML.
- **Interface utilisateur ML** (`api_ml/ui/`) : application Streamlit pour la prédiction et la visualisation interactive.
- **Base de données PostgreSQL** (`postgres/`) : stockage relationnel, initialisation automatisée.
- **Elasticsearch** (`elasticsearch/`) : moteur de recherche et d'indexation.
- **Monitoring Prometheus** (`prometheus/`) : collecte de métriques, configuration personnalisée.
- **Visualisation Grafana** (`grafana/`) : dashboards interactifs, provisioning automatisé.
- **Déploiement automatisé** (`srv/`) : scripts Bash, Terraform, Ansible, génération dynamique d'inventaire, configuration cloud.

---

## 📦 Démarrage rapide (local)

### Prérequis
- Docker et Docker Compose installés
- Ports suivants disponibles : 5432, 9999, 9998, 1000, 5000, 9870, 8088, 7077, 8000, 9000, 9001, 9200, 9090, 3000, 9997, 8501

### Lancement des services
```bash
docker compose build
# puis
docker compose up -d
```

### Arrêt des services
```bash
docker compose down
```

### Vérification
```bash
docker compose ps
```

---

## 🗺️ Architecture des services

| Service         | Port    | Description                                 |
|----------------|---------|---------------------------------------------|
| api            | 9999    | API FastAPI principale (fraude)             |
| sources_api    | 9998    | API d'ingestion de données                  |
| lakehouse      | 1000... | Orchestration, Spark, MLflow, MinIO, etc.   |
| postgres       | 5432    | Base de données relationnelle               |
| elasticsearch  | 9200    | Moteur de recherche                         |
| prometheus     | 9090    | Monitoring                                  |
| grafana        | 3000    | Visualisation                               |
| api_ml         | 9997    | API Machine Learning                        |
| ui_api_ml      | 8501    | Interface utilisateur Streamlit             |

---

## 🌐 Accès aux interfaces
- **API principale** : http://localhost:9999/docs (Swagger)
- **API sources** : http://localhost:9998/docs
- **Interface ML (Streamlit)** : http://localhost:8501
- **Grafana** : http://localhost:3000
- **Prometheus** : http://localhost:9090

---

## 🔬 Exemple d'appel API (prédiction)
```bash
curl -X POST "http://localhost:9999/predict" \
     -H "Content-Type: application/json" \
     -d '{ "feature1": 1.2, "feature2": 0.8, "feature3": 2.1 }'
```

Réponse attendue :
```json
{
  "prediction": 0,
  "probability": 0.15,
  "status": "success"
}
```

---

## 🛠️ Structure détaillée du projet

```
.
├── docker-compose.yml         # Orchestration multi-conteneurs (commenté)
├── api/                      # Backend FastAPI (routes, schémas, BDD, features)
│   ├── fastapi_app.py        # Application principale FastAPI
│   ├── database.py           # Connexion et gestion PostgreSQL
│   ├── schemas.py            # Modèles Pydantic
│   ├── routers/              # Routes modulaires (features, risques, etc.)
│   └── ...
├── sources_api/              # API d'ingestion, split, alimentation BDD
│   ├── api.py                # FastAPI pour ingestion
│   ├── db.py                 # Chargement CSV → PostgreSQL
│   ├── split.py              # Découpe de CSV (script commenté)
│   ├── requirements.txt      # Dépendances commentées
│   └── ...
├── lakehouse/                # Orchestration, pipeline, MLflow, Spark, MinIO
│   ├── orchestrator.py       # Orchestration globale (commenté)
│   ├── mlflow_minio_artifact_repo.py # Intégration MLflow/MinIO
│   ├── entrypoint.sh         # Script d'entrée (commenté)
│   ├── pipeline/             # Scripts pipeline (datamarts, feeder, ml, etc.)
│   └── ...
├── api_ml/                   # API ML et UI Streamlit
│   ├── api/main.py           # API FastAPI ML (commenté)
│   ├── ui/streamlit_app.py   # Interface Streamlit (commentée)
│   └── ...
├── postgres/                 # Base de données PostgreSQL (Dockerfile, init.sql commentés)
├── elasticsearch/            # Dockerfile commenté
├── prometheus/               # Dockerfile, prometheus.yml commentés
├── grafana/                  # Dockerfile commenté
├── srv/                      # Déploiement cloud (scripts, Ansible, Terraform)
│   ├── deploy_pipeline.sh    # Script Bash commenté
│   ├── ansible/              # Playbook, inventaire, templates commentés
│   ├── infra/                # main.tf, variables.tf commentés
│   └── ...
├── .lfsconfig                # Config LFS (commentée)
└── README.md                 # Ce fichier
```

---

## ⚙️ Déploiement cloud (optionnel)

Pour déployer sur AWS EC2 avec Terraform et Ansible (scripts commentés) :

```bash
cd srv
bash deploy_pipeline.sh
```

- Provisionnement de l'infra (tofu/Terraform)
- Génération dynamique de l'inventaire Ansible (template Jinja2)
- Déploiement automatisé de tous les services Docker sur les VMs

---

## 📝 Détail des fichiers de configuration et scripts

- **docker-compose.yml** : chaque service, port, dépendance et réseau est commenté pour expliquer son rôle.
- **requirements.txt** (sources_api/) : chaque dépendance est expliquée ligne par ligne.
- **split.py** (sources_api/) : script de découpe CSV, chaque section est commentée.
- **entrypoint.sh** (sources_api/, lakehouse/) : scripts d'entrée, commentaires sur chaque étape (attente BDD, alimentation, exécution).
- **orchestrator.py, mlflow_minio_artifact_repo.py** (lakehouse/) : orchestration, gestion artefacts, commentaires détaillés.
- **pipeline/** (lakehouse/) : chaque script (datamarts, feeder, ml, preprocessing, signals) est commenté pour expliquer la logique métier.
- **Dockerfile** (tous dossiers) : chaque étape d'installation, configuration, lancement de service est expliquée.
- **prometheus.yml** : chaque section de configuration et cible de monitoring est commentée.
- **init.sql** (postgres/) : script d'initialisation de la base, commentaires sur chaque commande SQL.
- **ansible/** (srv/) : playbook, inventaire, templates et scripts Python sont commentés pour expliquer le déploiement automatisé.
- **main.tf, variables.tf** (srv/infra/) : chaque ressource et variable Terraform est expliquée.
- **.lfsconfig** : configuration LFS, commentaire sur l'usage.

---

## 📚 Ressources utiles
- Documentation FastAPI : https://fastapi.tiangolo.com/
- Documentation Streamlit : https://docs.streamlit.io/
- Documentation Docker Compose : https://docs.docker.com/compose/
- Documentation Terraform : https://www.terraform.io/docs/
- Documentation Ansible : https://docs.ansible.com/

---

## 👤 Auteurs & contact
- Sidy Laye (https://gitlab.com/SidyLaye)
- Contributions bienvenues !

---

## 📝 Licence
Ce projet est distribué sous licence MIT.
