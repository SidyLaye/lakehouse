#!/usr/bin/env python3
import os
import pickle
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel

app = FastAPI(title="Fraud Detection API", version="1.0.0")

# === Pydantic models ===

class TransactionRaw(BaseModel):
    amount: float
    card_brand: str
    card_type: str
    merchant_state: str
    use_chip: str                # "True"/"False" or "yes"/"no"
    credit_limit: float
    per_capita_income: float
    yearly_income: float
    total_debt: float
    credit_score: Optional[float]
    num_credit_cards: Optional[int]

class PredictionResponse(BaseModel):
    fraud_probability: float
    is_fraud: bool
    confidence: str

# === Globals & paths ===

BASE_DIR    = Path(__file__).parent
MODEL_PATH  = BASE_DIR / "fraud_logreg.pkl"
PIPELINE_DIR = BASE_DIR / "pipeline/fraud_model_mlflow/sparkml"  # MLflow saved pipeline here

spark: Optional[SparkSession] = None
wrapper = None

# === Startup: init Spark & load wrapper ===

@app.on_event("startup")
async def startup_event():
    global spark, wrapper

    # 1) Start Spark
    spark = (
        SparkSession.builder
        .appName("FraudAPI")
        .master("local[*]")
        .config("spark.driver.memory", "8g")
        .getOrCreate()
    )

    # 2) Unpickle your SparkModelWrapper
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        wrapper = pickle.load(f)

    # 3) Override its path to point to the MLflow folder
    if not PIPELINE_DIR.exists():
        raise RuntimeError(f"Pipeline folder not found: {PIPELINE_DIR}")
    setattr(wrapper, "_model_dir", str(PIPELINE_DIR))

    print("✅ Loaded SparkModelWrapper with pipeline at:", PIPELINE_DIR)

# === Prediction helper ===

def predict_fraud(tx: TransactionRaw) -> PredictionResponse:
    if wrapper is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Build a Spark DataFrame with the raw columns your pipeline expects:
    def str_to_bool_flag(s: str) -> int:
        return int(str(s).strip().lower() in ["true", "1", "yes"])

    data = tx.dict()
    data["use_chip_bool"] = str_to_bool_flag(data.get("use_chip"))
    df = spark.createDataFrame([data])

    # Pipeline does:
    #   StringIndexer → OneHotEncoder → VectorAssembler → LogisticRegression
    preds = wrapper.predict(df).select("probability").head()
    p = float(preds["probability"][1])

    return PredictionResponse(
        fraud_probability=p,
        is_fraud      = p > 0.5,
        confidence    = "Haute" if abs(p - 0.5) > 0.3 else "Moyenne"
    )

# === Routes ===

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9997, log_level="info")
