from pydantic import BaseModel
from typing import Optional

# 1) ClientFeatures
class ClientFeatures(BaseModel):
    client_id: str
    tx_count: int
    avg_amount: Optional[float] = None
    std_amount: Optional[float] = None
    fraud_count: Optional[int] = None
    drop_count: Optional[int] = None
    unique_merchants: Optional[int] = None
    fraud_rate: Optional[float] = None
    drop_rate: Optional[float] = None

# 2) CardFeatures
class CardFeatures(BaseModel):
    tx_card_id: str
    card_type: Optional[str] = None
    tx_count: int
    fraud_count: Optional[int] = None
    avg_amount: Optional[float] = None
    drop_count: Optional[int] = None
    fraud_rate: Optional[float] = None
    drop_rate: Optional[float] = None

# 3) Velocity
class ClientVelocity(BaseModel):
    client_id: str
    avg_daily_txn: Optional[float] = None
    max_daily_txn: Optional[int] = None

# 4) MCCRisk
class MccRisk(BaseModel):
    mcc_code: str
    mcc_description: Optional[str] = None
    tx_count: Optional[int] = None
    fraud_count: Optional[int] = None
    drop_count: Optional[int] = None
    fraud_rate: Optional[float] = None
    drop_rate: Optional[float] = None

# 5) TimeDistribution
class TimeDistribution(BaseModel):
    hour: int
    tx_count: Optional[int] = None
    fraud_count: Optional[int] = None
    drop_count: Optional[int] = None
    fraud_rate: Optional[float] = None
    drop_rate: Optional[float] = None
