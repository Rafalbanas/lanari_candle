from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.order import OrderItemOut


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_pln: int
    is_active: bool = True
    image_url: Optional[str] = Field(default=None, max_length=512)
    stock_qty: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_pln: Optional[int] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(default=None, max_length=512)
    stock_qty: Optional[int] = Field(default=None, ge=0)


class OrderStatusUpdate(BaseModel):
    status: str


class AdminOrderOut(BaseModel):
    id: int
    status: str
    email: str
    full_name: str
    buyer_first_name: str
    buyer_last_name: str
    buyer_phone: str
    buyer_email: str
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_postal_code: str
    total_pln: int
    created_at: datetime
    items: List[OrderItemOut]
    shipping_method: str
    shipping_cost_pln: int
    shipping_country: str

    model_config = {"from_attributes": True}
