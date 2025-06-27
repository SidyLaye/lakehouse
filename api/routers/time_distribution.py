# Importation des modules nécessaires
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from database import get_connection, release_connection
from schemas import TimeDistribution

# Création du routeur FastAPI pour la distribution temporelle
router = APIRouter(prefix="/time_distribution", tags=["TimeDistribution"])

# Route GET pour lister la distribution temporelle avec pagination
@router.get("/", response_model=List[TimeDistribution])
def list_time_distribution(limit: int = Query(24, description="Nombre max de résultats (0–23 heures)"),
                           offset: int = Query(0, description="Offset pour la pagination")):
    """
    Récupère les lignes de dm_time_of_day_fraud, avec pagination (généralement 24 lignes max).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour récupérer la distribution temporelle
        query = f"""
            SELECT hour, tx_count, fraud_count, drop_count, fraud_rate, drop_rate
            FROM public.dm_time_of_day_fraud
            ORDER BY hour
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        result = []
        # Transformation des résultats SQL en objets Pydantic
        for r in rows:
            result.append(TimeDistribution(
                hour=r[0],
                tx_count=r[1],
                fraud_count=r[2],
                drop_count=r[3],
                fraud_rate=r[4],
                drop_rate=r[5],
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)

# Route GET pour récupérer la distribution d'une heure précise
@router.get("/{hour}", response_model=TimeDistribution)
def get_time_distribution(hour: int):
    """
    Récupère la distribution fraude pour une heure précise (0–23).
    """
    if hour < 0 or hour > 23:
        raise HTTPException(status_code=400, detail="L’heure doit être entre 0 et 23")
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour une heure précise
        query = f"""
            SELECT hour, tx_count, fraud_count, drop_count, fraud_rate, drop_rate
            FROM public.dm_time_of_day_fraud
            WHERE hour = %s
        """
        cur.execute(query, (hour,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Données non trouvées pour cette heure")
        return TimeDistribution(
            hour=row[0],
            tx_count=row[1],
            fraud_count=row[2],
            drop_count=row[3],
            fraud_rate=row[4],
            drop_rate=row[5],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)
