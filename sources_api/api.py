import os
import time
import sys
import mimetypes
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import logging

# — Configuration du dossier de données et paramètres de retry —
DATA_DIR = "transactions_fraud_datasets"
MAX_RETRIES = 5
SLEEP_BETWEEN = 10  # secondes

# — Configuration du logger —
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("raw-files-api")

# Création de l'application FastAPI
app = FastAPI(
    title="Raw Files API",
    description="Expose tels quels tous les fichiers du dossier transactions_fraud_datasets",
    version="1.0.0"
)

@app.on_event("startup")
def wait_for_data_dir():
    """
    Au démarrage, on s'assure que le dossier DATA_DIR existe,
    avec quelques tentatives avant d'abandonner.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        if os.path.isdir(DATA_DIR):
            logger.info(f"[startup] Found data dir '{DATA_DIR}' on attempt {attempt}")
            return
        logger.warning(f"[startup] '{DATA_DIR}' not found (attempt {attempt}/{MAX_RETRIES}), retrying in {SLEEP_BETWEEN}s…")
        time.sleep(SLEEP_BETWEEN)
    logger.error(f"[startup] Data dir '{DATA_DIR}' still missing after {MAX_RETRIES} attempts, exiting.")
    sys.exit(1)

# Route pour lister tous les fichiers disponibles dans DATA_DIR
@app.get("/files", response_model=List[str])
def list_files():
    """
    Retourne la liste alphabétique des noms de fichiers dans DATA_DIR.
    """
    try:
        return sorted(os.listdir(DATA_DIR))
    except Exception as e:
        logger.exception("Error listing files")
        raise HTTPException(status_code=500, detail=f"Impossible de lister '{DATA_DIR}': {e}")

# Route pour servir un fichier brut depuis DATA_DIR
@app.get("/files/{filename}")
def serve_file(filename: str):
    """
    Expose le fichier `filename` en brut, sans conversion ni parsing,
    en conservant son extension et son content-type d'origine.
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

    content_type, _ = mimetypes.guess_type(path)
    if content_type is None:
        content_type = "application/octet-stream"

    return FileResponse(
        path,
        media_type=content_type,
        filename=filename
    )

# Lancement local pour debug
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=9998, reload=True)
