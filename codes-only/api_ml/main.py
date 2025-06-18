# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pickle
import numpy as np
from pathlib import Path

app = FastAPI(title="Fraud Detection API", version="1.0.0")

# === MODÈLES PYDANTIC ===
class TransactionFeatures(BaseModel):
    features: List[float]

class PredictionResponse(BaseModel):
    fraud_probability: float
    is_fraud: bool
    confidence: str

# === CHARGEMENT DU MODÈLE ===
MODEL_PATH = "fraud_logreg.pkl"
model_data = None

def load_model():
    global model_data
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Modèle non trouvé: {MODEL_PATH}")
    
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    
    print(f"✅ Modèle chargé:")
    print(f"   - Coefficients: {len(model_data['coefficients'])}")
    print(f"   - Features: {len(model_data['feature_cols'])}")
    print(f"   - Intercept: {model_data['intercept']}")

# === FONCTION DE PRÉDICTION ===
def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -250, 250)))

def predict_fraud(features: List[float]) -> dict:
    if model_data is None:
        raise HTTPException(status_code=500, detail="Modèle non chargé")
    
    # Vérification de la taille
    expected_size = len(model_data['coefficients'])
    if len(features) != expected_size:
        raise HTTPException(
            status_code=400, 
            detail=f"Attendu {expected_size} features, reçu {len(features)}"
        )
    
    # Calcul : y = sigmoid(X * coefficients + intercept)
    features_array = np.array(features)
    linear_pred = np.dot(features_array, model_data['coefficients']) + model_data['intercept']
    probability = sigmoid(linear_pred)
    
    # Classification
    is_fraud = probability > 0.5
    confidence = "Haute" if abs(probability - 0.5) > 0.3 else "Moyenne"
    
    return {
        "fraud_probability": float(probability),
        "is_fraud": bool(is_fraud),
        "confidence": confidence
    }

# === ENDPOINTS ===
@app.on_event("startup")
async def startup_event():
    load_model()

@app.get("/")
async def root():
    return {"message": "Fraud Detection API", "status": "running"}

@app.get("/model/info")
async def model_info():
    if model_data is None:
        raise HTTPException(status_code=500, detail="Modèle non chargé")
    
    return {
        "model_type": "Logistic Regression",
        "num_features": len(model_data['coefficients']),
        "intercept": model_data['intercept'],
        "feature_columns": model_data['feature_cols']
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(transaction: TransactionFeatures):
    try:
        result = predict_fraud(transaction.features)
        return PredictionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# === ENDPOINT BATCH (optionnel) ===
@app.post("/predict/batch")
async def predict_batch(transactions: List[TransactionFeatures]):
    try:
        results = []
        for transaction in transactions:
            result = predict_fraud(transaction.features)
            results.append(result)
        return {"predictions": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
