from pydantic import BaseModel, Field, EmailStr
from typing import List


class OrderCreate(BaseModel):
    cart_id: int
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)


class CheckoutRequest(BaseModel):
    cart_id: int
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    name: str
    qty: int
    unit_price_pln: int
    line_total_pln: int


class OrderOut(BaseModel):
    id: int
    status: str
    cart_id: int
    email: EmailStr
    full_name: str
    items: List[OrderItemOut]
    total_pln: int