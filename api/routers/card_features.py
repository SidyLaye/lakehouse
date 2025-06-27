# Importation des modules nécessaires
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from database import get_connection, release_connection
from schemas import CardFeatures

# Création du routeur FastAPI pour les features carte
router = APIRouter(prefix="/card_features", tags=["CardFeatures"])

# Route GET pour lister les features carte avec pagination
@router.get("/", response_model=List[CardFeatures])
def list_card_features(limit: int = Query(100, description="Nombre max de résultats"), 
                       offset: int = Query(0, description="Offset pour la pagination")):
    """
    Récupère les lignes de dm_card_features, avec pagination.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour récupérer les features carte
        query = f"""
            SELECT tx_card_id, card_type, tx_count, fraud_count,
                   avg_amount, drop_count, fraud_rate, drop_rate
            FROM public.dm_card_features
            ORDER BY tx_card_id
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        result = []
        # Transformation des résultats SQL en objets Pydantic
        for r in rows:
            result.append(CardFeatures(
                tx_card_id=r[0],
                card_type=r[1],
                tx_count=r[2],
                fraud_count=r[3],
                avg_amount=r[4],
                drop_count=r[5],
                fraud_rate=r[6],
                drop_rate=r[7],
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)

# Route GET pour récupérer les features d'une carte spécifique
@router.get("/{tx_card_id}", response_model=CardFeatures)
def get_card_features(tx_card_id: str):
    """
    Récupère les features d'une carte donnée (par son tx_card_id).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour une carte précise
        query = f"""
            SELECT tx_card_id, card_type, tx_count, fraud_count,
                   avg_amount, drop_count, fraud_rate, drop_rate
            FROM public.dm_card_features
            WHERE tx_card_id = %s
        """
        cur.execute(query, (tx_card_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Carte non trouvée")
        return CardFeatures(
            tx_card_id=row[0],
            card_type=row[1],
            tx_count=row[2],
            fraud_count=row[3],
            avg_amount=row[4],
            drop_count=row[5],
            fraud_rate=row[6],
            drop_rate=row[7],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)
