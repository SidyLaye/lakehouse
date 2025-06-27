# Importation des modules nécessaires
import uvicorn
from fastapi import FastAPI
from routers import client_features, card_features, velocity, mcc_risk, time_distribution

# Création de l'application FastAPI avec titre, version et description
app = FastAPI(
    title="Fraud Detection Datamarts API",
    version="1.0.0",
    description="API pour interroger les datamarts produites par Spark dans PostgreSQL"
)

# Montage des routers pour chaque fonctionnalité (clients, cartes, etc.)
app.include_router(client_features.router)
app.include_router(card_features.router)
app.include_router(velocity.router)
app.include_router(mcc_risk.router)
app.include_router(time_distribution.router)

# Route racine pour vérifier que l'API fonctionne
@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l’API des datamarts fraud_detection"}

# Point d'entrée principal pour lancer l'API en local avec Uvicorn
if __name__ == "__main__":
    # Lancement en local pour tests
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=9999, reload=True)
