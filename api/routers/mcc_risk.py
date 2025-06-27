# Importation des modules nécessaires
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from database import get_connection, release_connection
from schemas import MccRisk

# Création du routeur FastAPI pour le risque MCC
router = APIRouter(prefix="/mcc_risk", tags=["MccRisk"])

# Route GET pour lister les risques MCC avec pagination
@router.get("/", response_model=List[MccRisk])
def list_mcc_risk(limit: int = Query(100, description="Nombre max de résultats"),
                  offset: int = Query(0, description="Offset pour la pagination")):
    """
    Récupère les lignes de dm_mcc_fraud_risk, avec pagination.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour récupérer les risques MCC
        query = f"""
            SELECT mcc_code, mcc_description, tx_count, fraud_count,
                   drop_count, fraud_rate, drop_rate
            FROM public.dm_mcc_fraud_risk
            ORDER BY mcc_code
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        result = []
        # Transformation des résultats SQL en objets Pydantic
        for r in rows:
            result.append(MccRisk(
                mcc_code=r[0],
                mcc_description=r[1],
                tx_count=r[2],
                fraud_count=r[3],
                drop_count=r[4],
                fraud_rate=r[5],
                drop_rate=r[6],
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)

# Route GET pour récupérer le risque d'un code MCC spécifique
@router.get("/{mcc_code}", response_model=MccRisk)
def get_mcc_risk(mcc_code: str):
    """
    Récupère le risque fraude d'un code MCC donné.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Requête SQL pour un MCC précis
        query = f"""
            SELECT mcc_code, mcc_description, tx_count, fraud_count,
                   drop_count, fraud_rate, drop_rate
            FROM public.dm_mcc_fraud_risk
            WHERE mcc_code = %s
        """
        cur.execute(query, (mcc_code,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="MCC non trouvé")
        return MccRisk(
            mcc_code=row[0],
            mcc_description=row[1],
            tx_count=row[2],
            fraud_count=row[3],
            drop_count=row[4],
            fraud_rate=row[5],
            drop_rate=row[6],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)
