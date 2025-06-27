#!/usr/bin/env python3
# === Importations ===
import os
import pickle
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel

# Création de l'application FastAPI
app = FastAPI(title="Fraud Detection API", version="1.0.0")

# === Modèles Pydantic pour la validation des données ===
class TransactionRaw(BaseModel):
    amount: float  # Montant de la transaction
    card_brand: str  # Marque de la carte
    card_type: str  # Type de carte
    merchant_state: str  # État du marchand
    use_chip: str  # Indique si la puce a été utilisée ("True"/"False")
    credit_limit: float  # Limite de crédit
    per_capita_income: float  # Revenu par habitant
    yearly_income: float  # Revenu annuel
    total_debt: float  # Dette totale
    credit_score: Optional[float]  # Score de crédit
    num_credit_cards: Optional[int]  # Nombre de cartes de crédit

class PredictionResponse(BaseModel):
    fraud_probability: float  # Probabilité de fraude
    is_fraud: bool           # Est-ce une fraude ?
    confidence: str          # Niveau de confiance

# === Variables globales et chemins des modèles ===
BASE_DIR    = Path(__file__).parent
MODEL_PATH  = BASE_DIR / "fraud_logreg.pkl"
PIPELINE_DIR = BASE_DIR / "pipeline/fraud_model_mlflow/sparkml"  # Dossier du pipeline MLflow

spark: Optional[SparkSession] = None
wrapper = None

# === Initialisation au démarrage : Spark et chargement du modèle ===
@app.on_event("startup")
async def startup_event():
    global spark, wrapper

    # 1) Démarrage de Spark
    spark = (
        SparkSession.builder
        .appName("FraudAPI")
        .master("local[*]")
        .config("spark.driver.memory", "8g")
        .getOrCreate()
    )

    # 2) Chargement du modèle picklé
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        wrapper = pickle.load(f)

    # 3) Redéfinition du chemin du pipeline MLflow
    if not PIPELINE_DIR.exists():
        raise RuntimeError(f"Pipeline folder not found: {PIPELINE_DIR}")
    setattr(wrapper, "_model_dir", str(PIPELINE_DIR))

    print("✅ Loaded SparkModelWrapper with pipeline at:", PIPELINE_DIR)

# === Fonction d'inférence/prédiction ===
def predict_fraud(tx: TransactionRaw) -> PredictionResponse:
    if wrapper is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Conversion de la variable use_chip en booléen (0/1)
    def str_to_bool_flag(s: str) -> int:
        return int(str(s).strip().lower() in ["true", "1", "yes"])

    data = tx.dict()
    data["use_chip_bool"] = str_to_bool_flag(data.get("use_chip"))
    df = spark.createDataFrame([data])

    # Passage dans le pipeline SparkML (StringIndexer, OneHotEncoder, VectorAssembler, LogisticRegression)
    preds = wrapper.predict(df).select("probability").head()
    p = float(preds["probability"][1])

    return PredictionResponse(
        fraud_probability=p,
        is_fraud      = p > 0.5,
        confidence    = "Haute" if abs(p - 0.5) > 0.3 else "Moyenne"
    )

# === Routes de l'API ===
@app.get("/")
async def root():
    return {"message": "Fraud Detection API", "status": "running"}

@app.get("/model/info")
async def model_info():
    if wrapper is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    return {
        "wrapper": type(wrapper).__name__,
        "pipeline_dir": wrapper._model_dir
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(tx: TransactionRaw):
    try:
        return predict_fraud(tx)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# === Lancement local (pour debug) ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9997, log_level="info")
