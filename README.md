# lakehouse
# lakehouse
# Fraud Detection API

## 🔧 Déploiement avec Docker Compose

### Prérequis

- Docker et Docker Compose installés
- Ports disponibles sur votre système

### Lancement rapide

```bash
# Construction et lancement des services
docker-compose build
docker-compose up -d

# Vérification des services
docker-compose ps
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

## 🎯 Interface Streamlit

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
docker-compose down
```

#### Consultation des logs

```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs fraud-api
docker-compose logs streamlit-app
```

#### Reconstruction après modification

```bash
docker-compose build --no-cache
docker-compose up -d
```

## 📊 Utilisation de l'API

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

## 🛠️ Développement

### Structure du projet

```
.
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py
│   └── model.pkl
├── streamlit/
│   ├── app.py
│   └── requirements.txt
├── test_fraud.json
└── README.md
```

### Logs et debugging

Pour suivre les logs en temps réel :

```bash
docker-compose logs -f
```

### Accès aux containers

```bash
# Accès au container API
docker-compose exec fraud-api bash

# Accès au container Streamlit
docker-compose exec streamlit-app bash
```
