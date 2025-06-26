from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from database import get_connection, release_connection
from schemas import ClientVelocity

router = APIRouter(prefix="/velocity", tags=["Velocity"])

@router.get("/", response_model=List[ClientVelocity])
def list_velocity(limit: int = Query(100, description="Nombre max de résultats"),
                  offset: int = Query(0, description="Offset pour la pagination")):
    """
    Récupère les lignes de dm_client_velocity, avec pagination.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"""
            SELECT client_id, avg_daily_txn, max_daily_txn
            FROM public.dm_client_velocity
            ORDER BY client_id
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append(ClientVelocity(
                client_id=r[0],
                avg_daily_txn=r[1],
                max_daily_txn=r[2],
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)

@router.get("/{client_id}", response_model=ClientVelocity)
def get_velocity(client_id: str):
    """
    Récupère la vélocité d'un client spécifique.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"""
            SELECT client_id, avg_daily_txn, max_daily_txn
            FROM public.dm_client_velocity
            WHERE client_id = %s
        """
        cur.execute(query, (client_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        return ClientVelocity(
            client_id=row[0],
            avg_daily_txn=row[1],
            max_daily_txn=row[2],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        release_connection(conn)
