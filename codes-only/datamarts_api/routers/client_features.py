from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from database import get_connection, release_connection
from schemas import ClientFeatures

router = APIRouter(prefix="/client_features", tags=["ClientFeatures"])

@router.get("/", response_model=List[ClientFeatures])
def list_client_features(limit: int = Query(100, description="Nombre max de résultats"), 
                         offset: int = Query(0, description="Offset pour la pagination")):
    """
    Récupère une liste de toutes les lignes de dm_client_features, avec pagination.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"""
            SELECT client_id, tx_count, avg_amount, std_amount,
                   fraud_count, drop_count, unique_merchants,
                   fraud_rate, drop_rate
            FROM public.dm_client_features
            ORDER BY client_id
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append(ClientFeatures(
                client_id=r[0],
                tx_count=r[1],
                avg_amount=r[2],
                std_amount=r[3],
                fraud_count=r[4],
                drop_count=r[5],
                unique_merchants=r[6],
                fraud_rate=r[7],
                drop_rate=r[8],
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)

@router.get("/{client_id}", response_model=ClientFeatures)
def get_client_features(client_id: str):
    """
    Récupère les features d'un client donné (par son client_id).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"""
            SELECT client_id, tx_count, avg_amount, std_amount,
                   fraud_count, drop_count, unique_merchants,
                   fraud_rate, drop_rate
            FROM public.dm_client_features
            WHERE client_id = %s
        """
        cur.execute(query, (client_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        return ClientFeatures(
            client_id=row[0],
            tx_count=row[1],
            avg_amount=row[2],
            std_amount=row[3],
            fraud_count=row[4],
            drop_count=row[5],
            unique_merchants=row[6],
            fraud_rate=row[7],
            drop_rate=row[8],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)
