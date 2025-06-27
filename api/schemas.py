# Importation de la base Pydantic et des types optionnels
from pydantic import BaseModel
from typing import Optional

# Schéma des features client (table dm_client_features)
class ClientFeatures(BaseModel):
    client_id: str  # Identifiant du client
    tx_count: int  # Nombre de transactions
    avg_amount: Optional[float] = None  # Montant moyen
    std_amount: Optional[float] = None  # Écart-type des montants
    fraud_count: Optional[int] = None  # Nombre de fraudes
    drop_count: Optional[int] = None  # Nombre d'abandons
    unique_merchants: Optional[int] = None  # Nombre de marchands uniques
    fraud_rate: Optional[float] = None  # Taux de fraude
    drop_rate: Optional[float] = None  # Taux d'abandon

# Schéma des features carte (table dm_card_features)
class CardFeatures(BaseModel):
    tx_card_id: str  # Identifiant de la carte
    card_type: Optional[str] = None  # Type de carte
    tx_count: int  # Nombre de transactions
    fraud_count: Optional[int] = None  # Nombre de fraudes
    avg_amount: Optional[float] = None  # Montant moyen
    drop_count: Optional[int] = None  # Nombre d'abandons
    fraud_rate: Optional[float] = None  # Taux de fraude
    drop_rate: Optional[float] = None  # Taux d'abandon

# Schéma de vélocité client (table dm_client_velocity)
class ClientVelocity(BaseModel):
    client_id: str  # Identifiant du client
    avg_daily_txn: Optional[float] = None  # Moyenne quotidienne de transactions
    max_daily_txn: Optional[int] = None  # Maximum quotidien de transactions

# Schéma de risque MCC (table dm_mcc_fraud_risk)
class MccRisk(BaseModel):
    mcc_code: str  # Code MCC
    mcc_description: Optional[str] = None  # Description du code MCC
    tx_count: Optional[int] = None  # Nombre de transactions
    fraud_count: Optional[int] = None  # Nombre de fraudes
    drop_count: Optional[int] = None  # Nombre d'abandons
    fraud_rate: Optional[float] = None  # Taux de fraude
    drop_rate: Optional[float] = None  # Taux d'abandon

# Schéma de distribution temporelle (table dm_time_of_day_fraud)
class TimeDistribution(BaseModel):
    hour: int  # Heure (0-23)
    tx_count: Optional[int] = None  # Nombre de transactions
    fraud_count: Optional[int] = None  # Nombre de fraudes
    drop_count: Optional[int] = None  # Nombre d'abandons
    fraud_rate: Optional[float] = None  # Taux de fraude
    drop_rate: Optional[float] = None  # Taux d'abandon
