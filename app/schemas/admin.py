from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.schemas.order import OrderItemOut

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_pln: int
    is_active: bool = True

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_pln: Optional[int] = None
    is_active: Optional[bool] = None

class OrderStatusUpdate(BaseModel):
    status: str

class AdminOrderOut(BaseModel):
    id: int
    status: str
    email: str
    full_name: str
    total_pln: int
    created_at: datetime
    items: List[OrderItemOut]

    model_config = {"from_attributes": True}
